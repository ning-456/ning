"""用户意图识别模块"""

import re
import os

import config


class IntentRecognizer:
    """用户意图识别引擎。

    通过关键词匹配判断用户问题是否与产品手册相关，
    以及是否为通用客服问题（物流、退货、发票、支付等）。
    采用宽松策略：只要包含与产品手册相关关键词即判定为相关，
    不确定时默认返回 True（允许通过）。
    """

    # 产品类别关键词 - 来自手册中的所有产品名称
    PRODUCT_KEYWORDS = [
        # VR/AR
        "vr", "头显", "虚拟现实", "头盔", "眼镜", "头戴",
        # 人体工学椅
        "椅", "工学椅", "座椅", "办公椅", "坐",
        # 健身单车
        "单车", "健身车", "动感单车", "骑行", "健身自行车",
        # 健身追踪器
        "手环", "追踪器", "运动手环", "心率", "计步", "运动监测", "智能手环",
        # 儿童电动摩托车
        "摩托车", "电动摩托", "儿童车", "骑乘",
        # 冰箱
        "冰箱", "冷藏", "冷冻", "保鲜", "冰柜",
        # 功能键盘
        "键盘", "机械键盘", "键帽", "按键", "打字",
        # 发电机
        "发电机", "发电", "电源", "备用电源", "汽油发电机",
        # 可编程温控器
        "温控", "温控器", "恒温", "温度控制", "恒温器",
        # 吹风机
        "吹风机", "吹风", "电吹风", "干发",
        # 摩托艇
        "摩托艇", "快艇", "水上", "水上摩托",
        # 水泵
        "水泵", "抽水", "泵", "排水", "潜水泵",
        # 洗碗机
        "洗碗机", "洗碗", "餐具", "清洗碗",
        # 烤箱
        "烤箱", "烘焙", "烤", "烤箱温度",
        # 电钻
        "电钻", "钻头", "钻孔", "冲击钻", "手电钻", "螺丝刀",
        # 相机
        "相机", "摄影", "拍照", "镜头", "摄像机", "单反", "数码相机",
        # 空气净化器
        "空气净化", "净化器", "空气过滤", "滤网", "PM2.5", "空气",
        # 空调
        "空调", "制冷", "制热", "变频", "遥控器",
        # 蒸汽清洁机
        "蒸汽清洁", "清洁机", "蒸汽", "高温清洁", "地板清洁",
        # 蓝牙激光鼠标
        "鼠标", "蓝牙鼠标", "激光鼠标", "无线鼠标", "光标",
        # 电视机
        "电视", "电视机", "液晶", "屏幕", "显示器", "高清",
        # 洗衣机
        "洗衣机", "洗衣", "滚筒", "洗衣服",
        # 电动牙刷
        "牙刷", "电动牙刷", "刷牙", "口腔",
        # 监控摄像头
        "摄像头", "监控", "安防", "摄像", "监控器",
        # 雪地摩托
        "雪地摩托", "雪地车", "雪橇",
        # 手持吸尘器
        "吸尘器", "吸尘", "手持吸尘", "除尘",
        # 通用产品相关词汇
        "说明书", "手册", "使用", "操作", "安装", "故障", "维修", "保养",
        "充电", "电池", "电源", "开关", "设置", "调节", "功能", "模式",
        "清洗", "更换", "检查", "注意", "警告", "安全",
        "怎么", "如何", "为什么", "什么", "多少", "哪里",
        # 英文产品关键词
        "manual", "product", "device", "appliance", "tool", "machine",
    ]

    # 通用客服问题关键词
    CS_KEYWORDS = [
        # 物流与配送
        "物流", "快递", "发货", "配送", "运输", "包裹", "签收", "物流单号",
        "什么时候到", "到货", "邮费", "运费", "包邮",
        # 退换货与退款
        "退货", "退款", "换货", "退换", "退钱", "退款到", "退货流程",
        "无理由", "退换货", "return", "refund",
        # 发票
        "发票", "开票", "税票", "电子发票", "invoice",
        # 支付
        "支付", "付款", "支付方式", "优惠券", "折扣", "满减", "优惠",
        "价格", "多少钱", "价格查询", "促销", "coupon",
        # 保修与维修
        "保修", "维修", "售后", "保修期", "warranty",
        "修", "维修点", "售后服", "质保",
        # 客服咨询
        "客服", "人工", "投诉", "建议", "feedback", "联系方式",
        "电话", "在线客服", "工作时间",
        # 订单相关
        "订单", "下单", "取消订单", "修改订单", "订单状态",
        "确认收货", "order",
    ]

    def __init__(self):
        """初始化意图识别器，从手册目录补充产品关键词。"""
        self._load_manual_keywords()

    def _load_manual_keywords(self):
        """从手册目录中的文件名提取产品关键词。"""
        try:
            manual_dir = config.MANUAL_DIR
            if os.path.isdir(manual_dir):
                for fname in os.listdir(manual_dir):
                    if fname.endswith(".txt"):
                        name = fname.replace("手册.txt", "").replace(".txt", "")
                        if name and len(name) <= 6:
                            self.PRODUCT_KEYWORDS.append(name)
        except Exception:
            pass

    def is_related_to_products(self, question: str) -> bool:
        """判断问题是否与产品手册内容相关。

        采用宽松的关键词匹配策略，只要问题中包含产品相关关键词
        即判定为相关。不确定时默认返回 True。

        Args:
            question: 用户提问文本

        Returns:
            True 表示与产品相关，False 表示不相关
        """
        if not question or not question.strip():
            return True

        question_lower = question.lower()

        for keyword in self.PRODUCT_KEYWORDS:
            if keyword.lower() in question_lower:
                return True

        # 如果检测到是通用的问题句式（有疑问词），也放行
        question_markers = ["吗", "呢", "么", "怎么", "如何", "为什么", "什么", "多少", "哪个", "哪些"]
        for marker in question_markers:
            if marker in question:
                return True

        # 默认宽松放行
        return True

    def is_cs_question(self, question: str) -> bool:
        """判断问题是否为通用客服咨询（物流、退货、发票、支付等）。

        注意：此方法仅判断是否为通用客服问题，不排除产品相关问题的可能性。
        用户可能同时询问产品使用与物流信息，此时两方法均返回 True。

        Args:
            question: 用户提问文本

        Returns:
            True 表示是通用客服问题
        """
        if not question or not question.strip():
            return False

        question_lower = question.lower()
        for keyword in self.CS_KEYWORDS:
            if keyword.lower() in question_lower:
                return True
        return False

    def get_intent_label(self, question: str) -> str:
        """获取意图标签（用于日志/调试）。

        Args:
            question: 用户提问文本

        Returns:
            意图标签：'product_related'、'cs_question' 或 'unrelated'
        """
        if self.is_related_to_products(question):
            return "product_related"
        if self.is_cs_question(question):
            return "cs_question"
        return "unrelated"
