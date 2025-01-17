import React, { useState } from 'react';
import { Layout, Form, Input, Button, Select, InputNumber, Radio, Card, List, message } from 'antd';
import { SearchOutlined, LoadingOutlined } from '@ant-design/icons';
import axios from 'axios';
import './App.css';

const { Header, Content } = Layout;
const { Option } = Select;

function App() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [savedPath, setSavedPath] = useState('');

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:5000/api/reddit/search', {
        mode: values.mode,
        query: values.query,
        limit: values.limit,
        timeFilter: values.timeFilter,
        sort: values.sort,
      });

      setResults(response.data.data);
      setSavedPath(response.data.filepath);
      message.success(`成功获取 ${response.data.total} 条数据`);
    } catch (error) {
      message.error(error.response?.data?.error || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const renderSortOptions = () => {
    const { mode } = form.getFieldsValue();
    if (!mode || mode === 'keyword') {
      return (
        <>
          <Option value="relevance">相关度</Option>
          <Option value="hot">热门</Option>
          <Option value="new">最新</Option>
          <Option value="comments">评论数</Option>
        </>
      );
    } else if (mode === 'subreddit') {
      return (
        <>
          <Option value="hot">热门</Option>
          <Option value="new">最新</Option>
          <Option value="top">最佳</Option>
        </>
      );
    } else if (mode === 'user') {
      return (
        <>
          <Option value="new">最新</Option>
          <Option value="hot">热门</Option>
          <Option value="top">最佳</Option>
        </>
      );
    }
    return null;
  };

  return (
    <Layout className="layout">
      <Header className="header">
        <h1 style={{ color: 'white' }}>Reddit数据采集系统</h1>
      </Header>
      <Content style={{ padding: '50px' }}>
        <Card title="搜索选项" style={{ marginBottom: 20 }}>
          <Form
            form={form}
            name="reddit_search"
            onFinish={onFinish}
            initialValues={{
              mode: 'keyword',
              limit: 5,
              timeFilter: 'all',
              sort: 'relevance',
            }}
          >
            <Form.Item
              name="mode"
              label="采集模式"
              rules={[{ required: true }]}
            >
              <Radio.Group>
                <Radio.Button value="keyword">关键词搜索</Radio.Button>
                <Radio.Button value="user">用户帖子</Radio.Button>
                <Radio.Button value="subreddit">板块内容</Radio.Button>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              name="query"
              label="搜索内容"
              rules={[{ required: true, message: '请输入搜索内容' }]}
            >
              <Input placeholder="输入关键词/用户名/板块名" />
            </Form.Item>

            <Form.Item
              name="limit"
              label="获取数量"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={100} />
            </Form.Item>

            <Form.Item
              name="timeFilter"
              label="时间范围"
              rules={[{ required: true }]}
            >
              <Select>
                <Option value="all">全部时间</Option>
                <Option value="day">24小时内</Option>
                <Option value="week">一周内</Option>
                <Option value="month">一个月内</Option>
                <Option value="year">一年内</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="sort"
              label="排序方式"
              rules={[{ required: true }]}
            >
              <Select>{renderSortOptions()}</Select>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" icon={loading ? <LoadingOutlined /> : <SearchOutlined />}>
                开始采集
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {results.length > 0 && (
          <Card title="采集结果" extra={`保存路径: ${savedPath}`}>
            <List
              itemLayout="vertical"
              dataSource={results}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={item.标题}
                    description={`作者: ${item.作者} | 评分: ${item.评分} | 评论数: ${item.评论数} | 发布时间: ${item.创建时间}`}
                  />
                  <div style={{ whiteSpace: 'pre-wrap' }}>{item.正文}</div>
                  {item.评论.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <h4>热门评论：</h4>
                      <List
                        size="small"
                        dataSource={item.评论}
                        renderItem={comment => (
                          <List.Item>
                            <List.Item.Meta
                              title={`${comment.作者} (评分: ${comment.评分})`}
                              description={comment.内容}
                            />
                          </List.Item>
                        )}
                      />
                    </div>
                  )}
                </List.Item>
              )}
            />
          </Card>
        )}
      </Content>
    </Layout>
  );
}

export default App;
