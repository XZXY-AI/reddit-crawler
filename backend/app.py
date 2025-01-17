from flask import Flask, request, jsonify, redirect, session, url_for
from flask_cors import CORS
import praw
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import time
import requests
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 为session添加密钥
CORS(app, supports_credentials=True)  # 启用CORS支持跨域请求，允许携带凭证

# 加载环境变量
load_dotenv()

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/authorize"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"

def init_reddit(access_token=None):
    """初始化Reddit客户端"""
    try:
        if access_token:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT'),
                token_manager={"access_token": access_token}
            )
        else:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT')
            )
        reddit.read_only = True
        return reddit
    except Exception as e:
        print(f"Reddit初始化失败: {str(e)}")
        return None

def save_to_json(data, mode, query, time_filter="all", sort="relevance"):
    """保存数据到JSON文件，按日期和查询条件组织"""
    # 创建基础输出目录
    base_dir = os.path.join(os.path.dirname(__file__), "..", "venv", "out")
    
    # 按年月日创建子目录
    date_dir = datetime.now().strftime('%Y%m%d')
    out_dir = os.path.join(base_dir, date_dir)
    
    # 创建模式子目录 (keyword/user/subreddit)
    mode_dir = os.path.join(out_dir, mode)
    
    # 确保目录存在
    os.makedirs(mode_dir, exist_ok=True)
    
    # 生成完整的文件路径
    timestamp = datetime.now().strftime('%H%M%S')
    if mode == "keyword":
        filename = f"{query}_{time_filter}_{sort}_{timestamp}.json"
    else:
        filename = f"{query}_{timestamp}.json"
    
    filepath = os.path.join(mode_dir, filename)
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def get_post_details(submission):
    """获取帖子的详细信息"""
    # 获取评论
    submission.comments.replace_more(limit=0)
    comments = []
    for comment in submission.comments.list()[:5]:
        comments.append({
            "作者": str(comment.author),
            "内容": comment.body,
            "评分": comment.score,
            "发布时间": datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S')
        })

    return {
        "标题": submission.title,
        "正文": submission.selftext,
        "评分": submission.score,
        "评论数": submission.num_comments,
        "创建时间": datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
        "作者": str(submission.author),
        "subreddit": str(submission.subreddit),
        "是否原创": submission.is_original_content,
        "是否自己的文本": submission.is_self,
        "评论": comments
    }

@app.route('/api/auth/url')
def get_auth_url():
    """获取Reddit授权URL"""
    state = secrets.token_urlsafe(16)
    session['state'] = state
    
    params = {
        'client_id': os.getenv('REDDIT_CLIENT_ID'),
        'response_type': 'code',
        'state': state,
        'redirect_uri': os.getenv('REDDIT_REDIRECT_URI'),
        'duration': 'temporary',
        'scope': 'read'
    }
    
    auth_url = f"{REDDIT_AUTH_URL}?{requests.compat.urlencode(params)}"
    return jsonify({'url': auth_url})

@app.route('/api/auth/callback')
def auth_callback():
    """处理Reddit的OAuth回调"""
    error = request.args.get('error')
    if error:
        return jsonify({'error': error}), 400
        
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    if state != session.get('state'):
        return jsonify({'error': 'Invalid state'}), 400
        
    # 获取访问令牌
    auth = requests.auth.HTTPBasicAuth(
        os.getenv('REDDIT_CLIENT_ID'),
        os.getenv('REDDIT_CLIENT_SECRET')
    )
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': os.getenv('REDDIT_REDIRECT_URI')
    }
    
    response = requests.post(REDDIT_TOKEN_URL, auth=auth, data=data)
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to get access token'}), 400
        
    token_data = response.json()
    session['access_token'] = token_data['access_token']
    
    # 重定向回前端
    return redirect(os.getenv('REDDIT_REDIRECT_URI'))

@app.route('/api/reddit/search', methods=['POST'])
def search_reddit():
    try:
        data = request.json
        mode = data.get('mode')
        query = data.get('query')
        limit = int(data.get('limit', 5))
        time_filter = data.get('timeFilter', 'all')
        sort = data.get('sort', 'relevance')

        access_token = session.get('access_token')
        reddit = init_reddit(access_token)
        if not reddit:
            return jsonify({"error": "Reddit初始化失败"}), 500

        results = []
        if mode == 'keyword':
            submissions = list(reddit.subreddit("all").search(
                query, 
                limit=limit,
                time_filter=time_filter,
                sort=sort
            ))
        elif mode == 'user':
            submissions = list(reddit.redditor(query).submissions.new(limit=limit))
        elif mode == 'subreddit':
            subreddit = reddit.subreddit(query)
            if sort == 'new':
                submissions = list(subreddit.new(limit=limit))
            elif sort == 'top':
                submissions = list(subreddit.top(limit=limit))
            else:
                submissions = list(subreddit.hot(limit=limit))
        else:
            return jsonify({"error": "无效的搜索模式"}), 400

        for submission in submissions:
            data = get_post_details(submission)
            results.append(data)
            time.sleep(1)  # 减少延迟时间，避免前端等待太久

        # 保存数据
        filepath = save_to_json(results, mode, query, time_filter, sort)
        
        return jsonify({
            "success": True,
            "data": results,
            "total": len(results),
            "filepath": filepath
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
