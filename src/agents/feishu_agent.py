"""飞书推送 Agent — 采用自定义应用推送"""
import json
import os
import time
import requests
from ..agents.base import AgentContext, BaseAgent
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_CHAT_ID


class FeishuPushAgent(BaseAgent):
    name = "feishu_push"
    description = "推送美股分析报告到飞书"

    def execute(self, context: AgentContext) -> AgentContext:
        if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
            context.warnings.append("飞书应用未配置，跳过推送")
            return context

        try:
            token = self._get_token()
            if not token:
                context.warnings.append("飞书 token 获取失败")
                return context

            content = self._build_content(context)
            payload = {
                "receive_id": FEISHU_CHAT_ID,
                "msg_type": "post",
                "content": json.dumps(content, ensure_ascii=False),
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            resp = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                headers=headers, json=payload, timeout=10,
            )
            result = resp.json()
            if result.get("code") == 0:
                context.warnings.append("飞书推送成功")
                self._send_image(token, context)
            else:
                context.warnings.append(f"飞书推送失败: {result}")
        except Exception as e:
            context.warnings.append(f"飞书推送异常: {e}")

        return context

    def _get_token(self) -> str:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
            timeout=10,
        )
        return resp.json().get("tenant_access_token", "")

    def _build_content(self, ctx: AgentContext) -> dict:
        lines = [[{"tag": "text", "text": f"📊 美股市场: {ctx.regime} | 股票: {len(ctx.stock_pool)}只 | 信号: {len(ctx.rl_signals)}个 | 回测: {len(ctx.backtest_results)}次"}]]
        lines.append([{"tag": "text", "text": ""}])

        # 热门板块
        if ctx.hot_sectors:
            lines.append([{"tag": "text", "text": "🔥 热门板块:"}])
            sectors = " | ".join([f"{s['sector']}(热度{s['heat_score']})" for s in ctx.hot_sectors[:5]])
            lines.append([{"tag": "text", "text": f"  {sectors}"}])
            lines.append([{"tag": "text", "text": ""}])

        # 市场研判
        if ctx.market_judgement:
            mj = ctx.market_judgement
            mj_line = f"市场阶段:{mj.get('market_phase','—')} | 趋势:{mj.get('trend_direction','—')} | 置信度:{mj.get('confidence','—')}"
            lines.append([{"tag": "text", "text": f"📊 市场研判:"}])
            lines.append([{"tag": "text", "text": f"  {mj_line}"}])
            lines.append([{"tag": "text", "text": ""}])

        # 交易信号（带详细理由）
        if ctx.rl_signals:
            buys = [s for s in ctx.rl_signals if s["action"] == "buy"]
            sells = [s for s in ctx.rl_signals if s["action"] == "sell"]
            lines.append([{"tag": "text", "text": f"📈 交易信号: 🟢买入{len(buys)}只 🔴卖出{len(sells)}只"}])
            lines.append([{"tag": "text", "text": ""}])
            if buys:
                lines.append([{"tag": "text", "text": "  🟢 买入信号:"}])
                for s in buys[:5]:
                    strategy = s.get("strategy", s.get("reason", "")[:20])
                    reason = s.get("reason", "")
                    lines.append([{"tag": "text", "text": f"    {s['stock']} | 置信度{s.get('confidence',0):.0%} | {strategy}"}])
                    if reason:
                        lines.append([{"tag": "text", "text": f"      {reason[:60]}"}])
                lines.append([{"tag": "text", "text": ""}])
            if sells:
                lines.append([{"tag": "text", "text": "  🔴 卖出信号:"}])
                for s in sells[:5]:
                    strategy = s.get("strategy", s.get("reason", "")[:20])
                    reason = s.get("reason", "")
                    lines.append([{"tag": "text", "text": f"    {s['stock']} | 置信度{s.get('confidence',0):.0%} | {strategy}"}])
                    if reason:
                        lines.append([{"tag": "text", "text": f"      {reason[:60]}"}])
                lines.append([{"tag": "text", "text": ""}])

        # 策略绩效
        if ctx.strategy_results:
            perf = ctx.strategy_results.get("strategy_performance", {})
            lines.append([{"tag": "text", "text": "📊 策略绩效:"}])
            for name, m in perf.items():
                lines.append([{"tag": "text", "text": f"  {name}: 收益{m.get('total_return',0):.1%} | S:{m.get('sharpe_ratio',0):.3f} | D:{m.get('max_drawdown',0):.1%}"}])
            lines.append([{"tag": "text", "text": ""}])

        # 风控
        if ctx.risk_metrics:
            dd = ctx.risk_metrics.get("drawdown", {})
            lines.append([{"tag": "text", "text": f"⚠️ 回撤: {dd.get('dd_pct',0):.1%} | 状态: {dd.get('level','normal')}"}])
            lines.append([{"tag": "text", "text": ""}])

        lines.append([{"tag": "text", "text": "💡 运行 python main.py --qa 进入问答模式"}])

        return {"zh_cn": {"title": f"🚀 美股量化日报 {ctx.date}", "content": lines}}

    def _send_image(self, token: str, ctx: AgentContext):
        viz_path = getattr(ctx, "viz_path", None)
        if not viz_path or not os.path.exists(viz_path):
            return
        try:
            with open(viz_path, "rb") as f:
                upload_resp = requests.post(
                    "https://open.feishu.cn/open-apis/im/v1/images",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"image": f},
                    data={"image_type": "message"},
                    timeout=20,
                )
            upload_result = upload_resp.json()
            if upload_result.get("code") != 0:
                ctx.warnings.append(f"飞书图片上传失败: {upload_result}")
                return
            image_key = upload_result["data"]["image_key"]
            payload = {
                "receive_id": FEISHU_CHAT_ID,
                "msg_type": "image",
                "content": json.dumps({"image_key": image_key}),
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            resp = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                headers=headers, json=payload, timeout=10,
            )
            if resp.json().get("code") == 0:
                ctx.warnings.append("飞书图片推送成功")
        except Exception as e:
            ctx.warnings.append(f"飞书图片推送异常: {e}")
