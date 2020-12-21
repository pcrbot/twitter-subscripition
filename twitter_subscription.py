import asyncio
import os
import pickle
import random
from typing import Dict, List

from hoshino import Service, priv
from hoshino.typing import CQEvent

"""
# 将以下三行添加到hoshino/modules/tiwtter/twitter.py 中的 twitter_poller 前，并注释掉原版 @sv.scheduled_job
from .twitter_subscription import TwitterSubscription
t_sub = TwitterSubscription(latest_info, poll_new_tweets)
t_sub.register_commands()


#@sv.scheduled_job('interval', seconds=_freq)
async def twitter_poller():
"""

sv = Service('twitter-subscription', use_priv=priv.ADMIN, manage_priv=priv.SUPERUSER, help_='订阅推/停止看推+账号')


class TwitterSubscription:
    SUB_DATA_FILE = './twitter_sub.cache'

    def __init__(self, latest_info: Dict[str, Dict], poll_new_tweets):
        # { account: {last_tweet_id: int, profile_image: str, media_only: bool, groups: List[int]} }
        self.latest_info = latest_info
        # poll new tweets function
        self.poll_new_tweets = poll_new_tweets

        # load subscription from saved file
        self.load_subs()

    def get_sub_accounts(self) -> List[str]:
        """
        return all subscribed twitter accounts
        """
        return [i for i in self.latest_info.keys()]

    def get_sub_groups(self, t_account: str) -> List[int]:
        """
        return all groups subscribed to specified account
        """
        return self.latest_info[t_account]['groups']

    def add_sub(self, t_account: str, group_id: int, media_only: bool = True):
        """
        subscribe a twitter account for a group
        """
        if t_account not in self.latest_info:
            self.latest_info[t_account] = {
                'last_tweet_id': 0, 'profile_image': '', 'media_only': media_only, 'groups': []
            }
        self.latest_info[t_account]['groups'].append(group_id)

    def add_sub_for_all(self, t_account: str):
        """
        subscribe a twitter account for all groups
        """
        self.add_sub(t_account, 0)

    def load_subs(self):
        """
        load subscription list from disk
        """
        if os.path.exists(self.SUB_DATA_FILE):
            with open(self.SUB_DATA_FILE, 'rb') as f:
                latest_infos = pickle.load(f)
                for t_account, t_sub in latest_infos.items():
                    if len(t_sub['groups']) == 0:
                        continue
                    t_sub['last_tweet_id'] = 0
                    self.latest_info[t_account] = t_sub

    def save_subs(self):
        """
        save subscription list to disk
        """
        with open(self.SUB_DATA_FILE, 'wb') as f:
            pickle.dump(self.latest_info, f)

    def register_commands(self):
        @sv.on_prefix('订阅推', only_to_me=True)
        async def subscribe(bot, ev: CQEvent):
            """
            subscribe a twitter account
            """
            args = ev.message.extract_plain_text().split()
            if args and len(args) > 0:
                t_account = args[0]
                if t_account in self.latest_info and ev.group_id in self.latest_info[t_account]['groups']:
                    return await bot.send(ev, '本群已经订阅过了噢')
                self.add_sub(t_account, ev.group_id)
                self.save_subs()
                return await bot.send(ev, f'订阅@{t_account}成功了噢')
            await bot.send(ev, '订阅失败了噢')

        @sv.on_prefix('停止看推', only_to_me=True)
        async def unsubscribe(bot, ev: CQEvent):
            """
            unsubscribe
            """
            args = ev.message.extract_plain_text().split()
            err = '您想取消哪个推呢'
            if args and len(args) > 0:
                t_account = args[0]
                if t_account in self.latest_info and ev.group_id in self.latest_info[t_account]['groups']:
                    self.latest_info[t_account]['groups'].pop(self.latest_info[t_account]['groups'].index(ev.group_id))
                    if len(self.latest_info[t_account]['groups']) == 0:
                        del self.latest_info[t_account]
                    return await bot.send(ev, f'退订@{t_account}成功了噢')
                else:
                    err = '本群没有订阅该推'
            await bot.send(ev, f'取消订阅失败了噢，{err}')

        @sv.on_prefix('本群订阅', only_to_me=True)
        async def sub_list(bot, ev: CQEvent):
            """
            list all subscription
            """
            t_accounts = []

            group_id = ev.group_id
            for t_account in self.get_sub_accounts():
                groups = self.get_sub_groups(t_account)
                if group_id in groups:
                    t_accounts.append('@' + t_account)
            if len(t_accounts) == 0:
                return await bot.send(ev, '本群没有订阅任何推哦')
            return await bot.send(ev, ', '.join(t_accounts))

        @sv.scheduled_job('interval', minutes=5)
        async def twitter_poller():
            """
            polls new tweets
            """
            buf = {}
            for t_account in self.get_sub_accounts():
                try:
                    buf[t_account] = await self.poll_new_tweets(t_account)
                    if l := len(buf[t_account]):
                        sv.logger.info(f"成功获取@{t_account}的新推文{l}条")
                    else:
                        sv.logger.info(f"未检测到@{t_account}的新推文")
                except Exception as e:
                    sv.logger.exception(e)
                    sv.logger.error(f"获取@{t_account}的推文时出现异常{type(e)}, 被群{self.get_sub_groups(t_account)}订阅")

            for t_account in self.get_sub_accounts():
                twts = []
                twts.extend(buf.get(t_account, []))
                await self.broadcast(sv, self.get_sub_groups(t_account), twts, sv.name)

    @staticmethod
    async def broadcast(self: Service, sub_groups, msgs: List[str], TAG='', interval_time=1, randomiser=None):
        """
        broadcast a message to specified groups
        """
        bot = self.bot
        g_list = await self.get_enable_groups()
        for gid, self_ids in g_list.items():
            if gid not in sub_groups and 0 not in sub_groups:
                continue
            try:
                for msg in msgs:
                    await asyncio.sleep(interval_time)
                    msg = randomiser(msg) if randomiser else msg
                    await bot.send_group_msg(self_id=random.choice(self_ids), group_id=gid, message=msg)
                l = len(msgs)
                if l:
                    self.logger.info(f"群{gid} 投递{TAG}成功 共{l}条消息")
            except Exception as e:
                self.logger.error(f"群{gid} 投递{TAG}失败：{type(e)}")
                self.logger.exception(e)
