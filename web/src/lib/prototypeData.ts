// ── 演示/兜底数据 ────────────────────────────────────
// 类型定义已迁移至 ./types.ts，此处仅保留数据常量。
// 款式兜底数据由 ./styles.ts 统一提供，避免与 importedStyles 重复维护。

import type { PrototypeBounty, PrototypeShop, StoreTask } from "./types";
import { inventoryStyles } from "./styles";

export type { PrototypeBounty, PrototypeShop, StoreTask };

// 款式 fallback — 复用 styles.ts 的 inventoryStyles
export { inventoryStyles as prototypeStyles };

// ── 店铺兜底数据 ────────────────────────────────────

export const prototypeShops: PrototypeShop[] = [
  {
    id: "celins-nail-futian",
    name: "Celins Nail瑟琳日式美甲美睫",
    distance: "1.8km",
    rating: 4.8,
    price: "¥158+",
    address: "福田区福华三路88号财富大厦15C",
    image: "/modao-assets/modao-14.jpg",
    tags: ["会展中心", "日系", "高空环境"],
    availableStyles: ["library-20260514-001", "library-20260514-002", "library-20260514-003"],
  },
  {
    id: "orchid-zhiguo-gangxia",
    name: "兰花芷国风·美甲美睫",
    distance: "2.1km",
    rating: 4.7,
    price: "¥168+",
    address: "福田区岗厦城E座1606室",
    image: "/modao-assets/modao-19.jpg",
    tags: ["国风", "咬残甲修复", "岗厦"],
    availableStyles: ["library-20260514-005", "library-20260514-012", "library-20260514-017"],
  },
  {
    id: "franli-jinzhonghuan",
    name: "法兰黎美甲美睫",
    distance: "2.4km",
    rating: 4.9,
    price: "¥128+",
    address: "福田区金田路3037号金中环商务大厦A座1131室",
    image: "/modao-assets/modao-17.jpg",
    tags: ["短甲友好", "来图还原", "会展中心"],
    availableStyles: ["library-20260514-004", "library-20260514-010", "library-20260514-021"],
  },
  {
    id: "yehe-chegongmiao",
    name: "野禾美睫美甲艺术研究院",
    distance: "3.0km",
    rating: 4.8,
    price: "¥138+",
    address: "福田区深南大道6007号创建大厦A座1508室",
    image: "/modao-assets/modao-22.jpg",
    tags: ["车公庙", "轻奢", "建构塑形"],
    availableStyles: ["library-20260514-006", "library-20260514-014", "library-20260514-024"],
  },
  {
    id: "huaqi-nail-mixc",
    name: "花岐美甲HUAQI Nail",
    distance: "5.8km",
    rating: 4.8,
    price: "¥167+",
    address: "南山区大冲新城花园2栋1D座2512室",
    image: "/modao-assets/modao-20.jpg",
    tags: ["万象天地", "日式流程", "开店14年"],
    availableStyles: ["library-20260514-008", "library-20260514-018", "library-20260514-030"],
  },
  {
    id: "pink-panda-mixc-world",
    name: "Pink Panda美甲美睫",
    distance: "6.2km",
    rating: 4.7,
    price: "¥300/人",
    address: "南山区深南大道大冲万象天地华润置地大厦E座27楼B",
    image: "/modao-assets/modao-23.jpg",
    tags: ["万象天地", "客制化", "设计感空间"],
    availableStyles: ["library-20260514-011", "library-20260514-023", "library-20260514-032"],
  },
];

export const prototypeBounties: PrototypeBounty[] = [
  {
    id: "bounty-crystal-long",
    title: "钻饰豹纹长甲复刻",
    budget: "¥250-350",
    status: "竞价中",
    image: "/modao-assets/bounty-013.png",
    participants: 8,
    deadline: "2天后截止",
    description: "想保留透明长甲、银色细闪、豹纹斑点和钻饰，可按手型微调。",
  },
  {
    id: "bounty-black-star",
    title: "黑色星星长甲改良",
    budget: "¥200-300",
    status: "待确认",
    image: "/modao-assets/bounty-011.png",
    participants: 5,
    deadline: "明晚截止",
    description: "保留黑色亮面、裸透底和星星元素，希望更适合日常拍照。",
  },
  {
    id: "bounty-silver-leopard",
    title: "银闪豹纹尖甲复刻",
    budget: "¥250-350",
    status: "竞价中",
    image: "/modao-assets/bounty-010.png",
    participants: 12,
    deadline: "3天后截止",
    description: "复刻银色渐变、豹纹点缀和尖形长甲，要求饰品位置自然。",
  },
];

export const storeTasks: StoreTask[] = [
  {
    id: "task-001",
    customer: "Coco",
    styleName: "极光蝴蝶",
    price: "¥218",
    distance: "3.2km",
    status: "待抢单",
    image: "/modao-assets/modao-05.jpg",
  },
  {
    id: "task-002",
    customer: "小林",
    styleName: "清透法式",
    price: "¥168",
    distance: "2.4km",
    status: "可接单",
    image: "/modao-assets/modao-01.jpg",
  },
  {
    id: "task-003",
    customer: "Mia",
    styleName: "彩虹琉璃",
    price: "¥258",
    distance: "5.1km",
    status: "竞价中",
    image: "/modao-assets/modao-22.jpg",
  },
];

export function getPrototypeStyle(id?: string) {
  return inventoryStyles.find((style) => style.id === id) ?? inventoryStyles[0];
}

export function getPrototypeBounty(id?: string) {
  return prototypeBounties.find((bounty) => bounty.id === id) ?? prototypeBounties[0];
}
