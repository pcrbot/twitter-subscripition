# twitter-subscripition

星乃的分群订阅推送，通过魔改 latest_info 实现分群订阅推送，订阅信息保存在 `./twitter_sub.cache` 文件中。

## 插入方法

1. 清空原版全局推送订阅列表 subr_dic
```python
subr_dic = {}
```

2. 将以下三行添加到hoshino/modules/tiwtter/twitter.py 中的 twitter_poller 前，并注释掉原版 @sv.scheduled_job
```python
from .twitter_subscription import TwitterSubscription
t_sub = TwitterSubscription(latest_info, poll_new_tweets)
t_sub.register_commands()


#@sv.scheduled_job('interval', seconds=_freq)
async def twitter_poller():
```

## 使用方法

以下均需at bot或呼叫bot，订阅列表

### 订阅推+twitter_id
如命令所示

### 停止看推+twitter_id
如命令所示

### 本群订阅
查看本群所有订阅
