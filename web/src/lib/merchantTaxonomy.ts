import type { NailTaxonomy } from "./types";

export const merchantTaxonomyLabels: Record<keyof NailTaxonomy, string> = {
  colors: "色系",
  techniques: "款式工艺",
  shapes: "甲型",
  styles: "风格",
  occasions: "适用场景",
  lengths: "长短",
};

export const merchantTaxonomyChoices: Record<keyof NailTaxonomy, string[]> = {
  colors: ["红色系", "粉色系", "蓝色系", "绿色系", "紫色系", "黑色系", "白色系", "灰色系", "裸色系", "大地色系", "金属色系", "金银色", "彩色", "多色", "冷色系"],
  techniques: ["亮片", "闪粉", "爆闪", "动物纹", "手绘", "花卉", "立体花", "法式", "法式变体", "渐变", "腮红", "冰透", "猫眼", "魔镜", "极光", "纯色", "跳色", "几何", "钻饰", "宝石", "珍珠"],
  shapes: ["尖型", "方圆型", "杏仁型", "梯型", "椭圆型", "圆形"],
  styles: ["仙气", "温柔", "梦幻", "复古", "老钱", "莫兰迪", "奢华", "巴洛克", "千金", "日系", "清新", "可爱", "暗黑", "朋克", "酷感", "极简", "冷淡", "INS", "欧美", "辣妹", "Y2K", "高级感", "轻奢", "气质"],
  occasions: ["婚礼", "新娘", "宴会", "日常", "通勤", "百搭", "春夏", "度假", "清凉", "派对", "蹦迪", "晚宴", "秋冬", "约会", "节日", "新年", "圣诞"],
  lengths: ["短款", "中长款", "长款"],
};

export const emptyMerchantTaxonomy = (): NailTaxonomy => ({
  colors: [],
  techniques: [],
  shapes: [],
  styles: [],
  occasions: [],
  lengths: [],
});
