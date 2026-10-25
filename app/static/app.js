const $ = (selector) => document.querySelector(selector);

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function setupDropzone(zoneSelector, inputSelector, labelSelector) {
  const zone = $(zoneSelector);
  const input = $(inputSelector);
  const label = $(labelSelector);
  ["dragenter", "dragover"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
  }));
  zone.addEventListener("drop", (event) => {
    input.files = event.dataTransfer.files;
    updateFileLabel(input, label);
  });
  input.addEventListener("change", () => updateFileLabel(input, label));
}

function updateFileLabel(input, label) {
  const files = [...input.files];
  label.textContent = files.length ? files.map((file) => file.name).join("、") : "尚未选择文件";
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((item) => item.classList.toggle("active", item.id === `panel-${name}`));
  if (name === "format") loadFormatJournalStyles();
  if (name === "history") { loadHistory(); loadStats(); }
  if (name === "journals") loadJournalStyles();
}

function activateTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
}

const schoolProfiles = [
  { keys: ["清华", "北京大学", "北大", "浙江大学", "复旦", "上海交通", "南京大学", "中国科学技术大学", "中科大", "武汉大学", "华中科技", "西安交通", "中山大学", "同济", "哈尔滨工业", "南开", "天津大学", "北京师范", "中国人民大学"], group: "高校论文通用模板", style: "GB/T 7714-2015", note: "当前为常见高校论文规范建议。学校会按院系、专业和学历层次发布不同模板，请优先核对学校官方最新版。" },
  { keys: ["大学", "学院", "职业技术"], group: "高校论文通用模板", style: "GB/T 7714-2015", note: "暂未收录该校官方模板，先按国内论文常用规范推荐；请核对学校或院系发布的模板。" },
];

const schoolCatalog = [
  { name: "北京大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "清华大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "中国人民大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "北京师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "北京理工大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "北京航空航天大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "北京交通大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "北京科技大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "北京邮电大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "北京工业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "北京化工大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "北京林业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "北京外国语大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中国农业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "中国政法大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中央财经大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "首都师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "首都医科大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "中国科学院大学", levels: ["graduate", "doctoral"] }, { name: "中国社会科学院大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "复旦大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "上海交通大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "同济大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "华东师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "上海大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "上海理工大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "上海师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "上海应用技术大学", levels: ["undergraduate", "graduate"] },
  { name: "浙江大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "浙江工业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "浙江师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "宁波大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "杭州电子科技大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "温州医科大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "南京大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "东南大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "南京师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "苏州大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "扬州大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "江苏大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "南京邮电大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "南京工业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "武汉大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "华中科技大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "华中师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中南财经政法大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "武汉理工大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "湖北大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "四川大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "电子科技大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "西南交通大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "成都理工大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "西南财经大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "重庆大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "西南大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "重庆邮电大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "西安交通大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "西北工业大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "西北大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "西安理工大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "哈尔滨工业大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "哈尔滨工程大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "东北林业大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "吉林大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "东北师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "南开大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "天津大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "天津师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "山东大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中国海洋大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "青岛大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "山东师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "中山大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "华南理工大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "暨南大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "华南师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "深圳大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "厦门大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "福州大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "福建师范大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "湖南大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中南大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "湖南师范大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "郑州大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "河南大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "中国科学技术大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "安徽大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "云南大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "兰州大学", levels: ["undergraduate", "graduate", "doctoral"] }, { name: "海南大学", levels: ["undergraduate", "graduate", "doctoral"] },
  { name: "深圳职业技术大学", levels: ["associate", "undergraduate"] }, { name: "金华职业技术大学", levels: ["associate", "undergraduate"] },
  { name: "无锡职业技术大学", levels: ["associate", "undergraduate"] }, { name: "浙江机电职业技术大学", levels: ["associate", "undergraduate"] },
  { name: "南京工业职业技术大学", levels: ["associate", "undergraduate"] }, { name: "河北科技工程职业技术大学", levels: ["associate", "undergraduate"] },
  { name: "广东轻工职业技术大学", levels: ["associate", "undergraduate"] }, { name: "广州职业技术大学", levels: ["associate", "undergraduate"] },
  { name: "北京电子科技职业学院", levels: ["associate"] }, { name: "北京工业职业技术学院", levels: ["associate"] },
  { name: "天津市职业大学", levels: ["associate"] }, { name: "上海电子信息职业技术学院", levels: ["associate"] },
  { name: "江苏农林职业技术学院", levels: ["associate"] }, { name: "无锡商业职业技术学院", levels: ["associate"] },
  { name: "浙江金融职业学院", levels: ["associate"] }, { name: "宁波职业技术学院", levels: ["associate"] },
  { name: "黄河水利职业技术学院", levels: ["associate"] }, { name: "深圳信息职业技术学院", levels: ["associate"] },
  { name: "广州番禺职业技术学院", levels: ["associate"] }, { name: "长沙民政职业技术学院", levels: ["associate"] },
  { name: "重庆工业职业技术学院", levels: ["associate"] }, { name: "成都航空职业技术学院", levels: ["associate"] },
  { name: "陕西工业职业技术学院", levels: ["associate"] }, { name: "山东商业职业技术学院", levels: ["associate"] }
];

const schoolCityAliases = {
  "北京": ["北京", "首都"], "上海": ["上海"], "天津": ["天津"], "重庆": ["重庆"], "河北": ["河北", "石家庄", "秦皇岛", "保定", "唐山", "廊坊", "张家口"],
  "山西": ["山西", "太原"], "辽宁": ["辽宁", "沈阳", "大连"], "吉林": ["吉林", "长春"], "黑龙江": ["黑龙江", "哈尔滨"], "江苏": ["江苏", "南京", "苏州", "无锡", "扬州", "徐州", "常州"],
  "浙江": ["浙江", "杭州", "宁波", "温州", "金华"], "安徽": ["安徽", "合肥"], "福建": ["福建", "福州", "厦门", "泉州"], "江西": ["江西", "南昌"], "山东": ["山东", "济南", "青岛", "烟台"],
  "河南": ["河南", "郑州", "开封", "洛阳"], "湖北": ["湖北", "武汉", "宜昌"], "湖南": ["湖南", "长沙", "湘潭"], "广东": ["广东", "广州", "深圳", "珠海", "汕头", "佛山"],
  "海南": ["海南", "海口"], "四川": ["四川", "成都", "绵阳"], "贵州": ["贵州", "贵阳"], "云南": ["云南", "昆明"], "陕西": ["陕西", "西安"],
  "甘肃": ["甘肃", "兰州"], "青海": ["青海", "西宁"], "内蒙古": ["内蒙古", "呼和浩特", "包头"], "广西": ["广西", "南宁", "桂林"],
  "西藏": ["西藏", "拉萨"], "宁夏": ["宁夏", "银川"], "新疆": ["新疆", "乌鲁木齐"], "香港": ["香港"], "澳门": ["澳门"]
};

const additionalSchoolsByRegion = {
  "北京": "北京工商大学 北京建筑大学 北京信息科技大学 北京第二外国语学院 北京服装学院 北京印刷学院 北京物资学院 北京石油化工学院 北京农学院 北京联合大学 北京城市学院 北京电子科技职业学院 北京工业职业技术学院 北京信息职业技术学院 北京农业职业学院",
  "上海": "华东理工大学 东华大学 上海财经大学 上海外国语大学 上海海事大学 上海海洋大学 上海电力大学 上海政法学院 上海戏剧学院 上海音乐学院 上海健康医学院 上海城建职业学院 上海工艺美术职业学院",
  "天津": "天津医科大学 天津工业大学 天津科技大学 天津理工大学 天津财经大学 天津商业大学 天津城建大学 天津职业技术师范大学 天津中医药大学 天津市职业大学 天津医学高等专科学校",
  "河北": "河北大学 河北工业大学 燕山大学 河北师范大学 河北农业大学 河北医科大学 河北经贸大学 河北工程大学 石家庄铁道大学 华北理工大学 河北科技大学 河北地质大学 河北金融学院 河北建筑工程学院 石家庄职业技术学院 邯郸职业技术学院",
  "山西": "山西大学 太原理工大学 中北大学 山西医科大学 山西师范大学 山西财经大学 太原科技大学 山西农业大学 山西大同大学 山西工程科技职业大学 山西省财政税务专科学校",
  "辽宁": "大连理工大学 东北大学 辽宁大学 大连海事大学 沈阳工业大学 沈阳航空航天大学 沈阳建筑大学 辽宁师范大学 大连医科大学 中国医科大学 沈阳药科大学 东北财经大学 大连民族大学 辽宁科技大学 大连职业技术学院",
  "吉林": "东北电力大学 长春理工大学 长春工业大学 延边大学 长春中医药大学 吉林农业大学 长春师范大学 吉林财经大学 北华大学 长春大学 长春职业技术学院 吉林交通职业技术学院",
  "黑龙江": "东北农业大学 东北石油大学 黑龙江大学 哈尔滨医科大学 黑龙江中医药大学 哈尔滨师范大学 黑龙江科技大学 齐齐哈尔大学 佳木斯大学 黑龙江八一农垦大学 黑龙江职业学院",
  "江苏": "河海大学 中国矿业大学 江南大学 南京航空航天大学 南京理工大学 南京林业大学 南京信息工程大学 南京医科大学 南京中医药大学 南京财经大学 南京审计大学 常州大学 南通大学 徐州医科大学 盐城工学院 常州信息职业技术学院",
  "浙江": "中国美术学院 浙江工商大学 浙江财经大学 浙江理工大学 中国计量大学 浙江农林大学 浙江中医药大学 浙江海洋大学 湖州师范学院 绍兴文理学院 嘉兴大学 浙江传媒学院 浙江艺术职业学院",
  "安徽": "合肥工业大学 安徽师范大学 安徽农业大学 安徽医科大学 安徽财经大学 安徽工业大学 安徽理工大学 安徽建筑大学 安徽中医药大学 蚌埠医科大学 淮北师范大学 合肥大学 安徽职业技术学院 芜湖职业技术学院",
  "福建": "华侨大学 集美大学 福建农林大学 福建医科大学 福建中医药大学 闽南师范大学 闽江学院 福建理工大学 厦门理工学院 黎明职业大学 福建船政交通职业学院",
  "江西": "南昌大学 江西师范大学 江西财经大学 江西农业大学 江西理工大学 华东交通大学 南昌航空大学 景德镇陶瓷大学 东华理工大学 江西中医药大学 赣南师范大学 宜春学院 九江学院 江西应用技术职业学院",
  "山东": "中国石油大学（华东） 山东科技大学 济南大学 青岛科技大学 青岛理工大学 齐鲁工业大学 山东农业大学 山东财经大学 山东中医药大学 济宁医学院 曲阜师范大学 鲁东大学 聊城大学 临沂大学 烟台大学 潍坊学院 山东职业学院",
  "河南": "河南科技大学 河南理工大学 河南农业大学 河南师范大学 河南财经政法大学 河南工业大学 华北水利水电大学 郑州轻工业大学 新乡医学院 河南中医药大学 洛阳师范学院 信阳师范大学 河南职业技术学院",
  "湖北": "中国地质大学（武汉） 华中农业大学 中南民族大学 武汉科技大学 湖北工业大学 武汉工程大学 武汉纺织大学 湖北中医药大学 三峡大学 长江大学 湖北师范大学 湖北经济学院 武汉职业技术学院",
  "湖南": "湘潭大学 湖南农业大学 湖南科技大学 南华大学 吉首大学 湖南中医药大学 长沙理工大学 湖南工商大学 湖南工业大学 湖南理工学院 湖南第一师范学院 湖南信息职业技术学院",
  "广东": "南方医科大学 广州医科大学 广东工业大学 广东外语外贸大学 广东财经大学 汕头大学 广东海洋大学 广州中医药大学 广东药科大学 五邑大学 东莞理工学院 佛山大学 仲恺农业工程学院 广东技术师范大学 顺德职业技术学院",
  "广西": "广西大学 广西师范大学 桂林电子科技大学 桂林理工大学 广西医科大学 广西民族大学 广西中医药大学 南宁师范大学 广西科技大学 北部湾大学 广西职业技术学院",
  "海南": "海南师范大学 海南医科大学 海南热带海洋学院 海南职业技术学院",
  "四川": "西南石油大学 成都中医药大学 四川农业大学 西南科技大学 成都信息工程大学 四川师范大学 西华大学 成都大学 西南民族大学 成都医学院 四川轻化工大学 四川职业技术学院",
  "重庆": "西南政法大学 重庆医科大学 重庆师范大学 重庆交通大学 重庆工商大学 重庆理工大学 四川外国语大学 重庆科技大学 重庆文理学院 重庆三峡学院 重庆工程职业技术学院",
  "贵州": "贵州大学 贵州师范大学 贵州医科大学 贵州财经大学 贵州民族大学 贵州中医药大学 遵义医科大学 贵州师范学院 铜仁学院 贵州交通职业技术学院",
  "云南": "昆明理工大学 云南师范大学 云南农业大学 昆明医科大学 云南财经大学 西南林业大学 云南民族大学 大理大学 云南中医药大学 曲靖师范学院 昆明冶金高等专科学校",
  "陕西": "西北农林科技大学 西安电子科技大学 长安大学 陕西师范大学 西北政法大学 西安建筑科技大学 西安科技大学 陕西科技大学 西安邮电大学 西安石油大学 延安大学 陕西中医药大学 西安航空职业技术学院",
  "甘肃": "西北师范大学 兰州理工大学 兰州交通大学 甘肃农业大学 甘肃中医药大学 西北民族大学 兰州财经大学 天水师范学院 兰州职业技术学院",
  "青海": "青海大学 青海师范大学 青海民族大学 青海卫生职业技术学院",
  "内蒙古": "内蒙古大学 内蒙古工业大学 内蒙古农业大学 内蒙古师范大学 内蒙古科技大学 内蒙古医科大学 内蒙古民族大学 内蒙古财经大学 包头职业技术学院",
  "宁夏": "宁夏大学 北方民族大学 宁夏医科大学 宁夏师范学院 宁夏职业技术学院",
  "新疆": "新疆大学 石河子大学 新疆农业大学 新疆师范大学 新疆医科大学 新疆财经大学 塔里木大学 伊犁师范大学 喀什大学 新疆职业大学",
  "西藏": "西藏大学 西藏民族大学 西藏农牧大学 西藏藏医药大学",
  "香港": "香港中文大学 香港科技大学 香港理工大学 香港城市大学 香港浸会大学 香港教育大学 岭南大学",
  "澳门": "澳门科技大学 澳门理工大学 澳门城市大学 澳门旅游大学"
};
const moreSchoolsByRegion = {
  "北京": "北京语言大学 中央民族大学 中国矿业大学（北京） 中国石油大学（北京） 中国地质大学（北京） 北京中医药大学 外交学院 国际关系学院 中国劳动关系学院 中华女子学院 北京财贸职业学院",
  "上海": "上海交通大学医学院 上海对外经贸大学 上海工程技术大学 上海立信会计金融学院 上海商学院 上海第二工业大学 上海旅游高等专科学校",
  "天津": "天津外国语大学 天津体育学院 天津美术学院 天津音乐学院 天津农学院 天津中德应用技术大学 天津轻工职业技术学院",
  "河北": "华北电力大学（保定） 中央司法警官学院 防灾科技学院 华北科技学院 河北中医药大学 河北传媒学院 河北美术学院 河北环境工程学院 承德医学院 唐山师范学院 邢台学院 河北石油职业技术大学",
  "山西": "山西中医药大学 太原师范学院 长治医学院 晋中学院 运城学院 忻州师范学院 山西警察学院 山西药科职业学院",
  "辽宁": "沈阳农业大学 沈阳师范大学 沈阳化工大学 大连工业大学 大连交通大学 大连海洋大学 沈阳理工大学 辽宁石油化工大学 渤海大学 辽宁工程技术大学 辽宁轨道交通职业学院",
  "吉林": "吉林师范大学 长春中医药大学 吉林建筑大学 吉林化工学院 吉林工程技术师范学院 吉林艺术学院 吉林农业科技学院 长春金融高等专科学校",
  "黑龙江": "东北农业大学 东北林业大学 哈尔滨商业大学 哈尔滨体育学院 黑龙江工程学院 黑龙江东方学院 绥化学院 牡丹江师范学院 大庆师范学院 黑龙江护理高等专科学校",
  "江苏": "南京林业大学 南京艺术学院 南京体育学院 南京工程学院 南京晓庄学院 淮阴师范学院 淮阴工学院 盐城师范学院 江苏师范大学 江苏科技大学 常熟理工学院 金陵科技学院 苏州科技大学 泰州学院 南京铁道职业技术学院",
  "浙江": "杭州师范大学 浙江万里学院 浙江科技大学 浙江外国语学院 浙江音乐学院 浙江警察学院 浙江水利水电学院 衢州学院 台州学院 丽水学院 浙江树人学院 浙江工商职业技术学院",
  "安徽": "安徽工程大学 安徽中医药大学 安庆师范大学 淮北师范大学 阜阳师范大学 合肥师范学院 滁州学院 皖南医学院 安徽艺术学院 安徽新华学院 安徽商贸职业技术学院",
  "福建": "福建江夏学院 三明学院 龙岩学院 莆田学院 宁德师范学院 福建警察学院 福建商学院 厦门医学院 福建幼儿师范高等专科学校",
  "江西": "江西科技师范大学 南昌工程学院 景德镇学院 萍乡学院 新余学院 井冈山大学 赣南医科大学 江西警察学院 豫章师范学院 江西外语外贸职业学院",
  "山东": "山东第一医科大学 山东建筑大学 山东理工大学 青岛农业大学 临沂大学 山东艺术学院 山东工艺美术学院 山东交通学院 山东政法学院 山东女子学院 潍坊医学院 滨州医学院 德州学院 枣庄学院 菏泽学院 日照职业技术学院",
  "河南": "河南科技学院 河南牧业经济学院 安阳师范学院 南阳师范学院 商丘师范学院 周口师范学院 洛阳理工学院 河南工程学院 郑州航空工业管理学院 平顶山学院 黄淮学院 河南财政金融学院 河南医学高等专科学校",
  "湖北": "武汉工程大学 武汉轻工大学 湖北文理学院 湖北汽车工业学院 湖北民族大学 湖北工程学院 湖北理工学院 黄冈师范学院 湖北第二师范学院 武汉商学院 湖北美术学院 湖北警官学院 湖北职业技术学院",
  "湖南": "湖南农业大学 湖南工程学院 湖南文理学院 怀化学院 邵阳学院 湖南城市学院 湖南科技学院 湖南女子学院 长沙学院 湘南学院 湖南警察学院 湖南工艺美术职业学院",
  "广东": "广州大学 广州航海学院 广东海洋大学 广东第二师范学院 韶关学院 惠州学院 韩山师范学院 肇庆学院 嘉应学院 岭南师范学院 广东金融学院 广东警官学院 星海音乐学院 广州美术学院 广东科学技术职业学院",
  "广西": "广西医科大学 广西艺术学院 桂林医科大学 广西财经学院 玉林师范学院 河池学院 百色学院 梧州学院 贺州学院 广西民族师范学院 桂林航天工业学院 柳州职业技术大学",
  "海南": "海南大学 海南师范大学 三亚学院 琼台师范学院 海南科技职业大学 海南经贸职业技术学院",
  "四川": "西华师范大学 西南医科大学 川北医学院 成都体育学院 四川音乐学院 西南石油大学 成都师范学院 乐山师范学院 绵阳师范学院 内江师范学院 宜宾学院 成都工业学院 四川民族学院 四川旅游学院 四川建筑职业技术学院",
  "重庆": "重庆邮电大学 重庆医科大学 重庆师范大学 重庆文理学院 长江师范学院 重庆第二师范学院 重庆三峡学院 四川美术学院 重庆警察学院 重庆财经学院 重庆电力高等专科学校",
  "贵州": "贵州理工学院 贵州商学院 贵州警察学院 六盘水师范学院 凯里学院 安顺学院 兴义民族师范学院 贵州工程应用技术学院 贵州电子信息职业技术学院",
  "云南": "云南艺术学院 云南警官学院 昆明学院 红河学院 玉溪师范学院 楚雄师范学院 文山学院 保山学院 昭通学院 云南经济管理学院 云南交通职业技术学院",
  "陕西": "西安工业大学 西安工程大学 西安外国语大学 西安财经大学 西安美术学院 西安音乐学院 宝鸡文理学院 咸阳师范学院 渭南师范学院 榆林学院 商洛学院 安康学院 西安文理学院 陕西学前师范学院",
  "甘肃": "兰州城市学院 河西学院 陇东学院 甘肃政法大学 甘肃民族师范学院 兰州工业学院 兰州文理学院 甘肃医学院 酒泉职业技术学院",
  "青海": "青海大学昆仑学院 青海警官职业学院 青海农牧科技职业学院",
  "内蒙古": "内蒙古民族大学 呼伦贝尔学院 赤峰学院 集宁师范学院 河套学院 鄂尔多斯应用技术学院 内蒙古艺术学院 内蒙古警察职业学院",
  "宁夏": "宁夏理工学院 宁夏大学新华学院 银川能源学院 宁夏警官职业学院",
  "新疆": "新疆医科大学 新疆艺术学院 新疆工程学院 昌吉学院 新疆理工学院 新疆政法学院 新疆警察学院 和田师范专科学校",
  "香港": "香港大学 香港大学专业进修学院 香港恒生大学 香港树仁大学 香港都会大学 香港高等教育科技学院",
  "澳门": "澳门大学 澳门理工大学 澳门镜湖护理学院 澳门圣若瑟大学"
};
const associateOnlyPattern = /(职业技术学院|职业学院|高等专科学校|专科学校|职业大学|职业技术大学|技师学院|工业职业学院|商业职业学院|医学高等专科学校)/;
for (const [region, names] of Object.entries({ ...additionalSchoolsByRegion, ...moreSchoolsByRegion })) {
  const aliases = schoolCityAliases[region] || [region];
  for (const name of names.split(/\s+/).filter(Boolean)) {
    const existing = schoolCatalog.find((school) => school.name === name);
    const levels = associateOnlyPattern.test(name) ? ["associate"] : ["undergraduate", "graduate"];
    if (!existing) schoolCatalog.push({ name, levels });
    else existing.levels = [...new Set([...existing.levels, ...levels])];
  }
}
const schoolCityIndex = new Map();
for (const [province, names] of Object.entries({ ...additionalSchoolsByRegion, ...moreSchoolsByRegion })) {
  const aliases = schoolCityAliases[province] || [province];
  const regionNames = new Set(names.split(/\s+/).filter(Boolean));
  const schools = schoolCatalog.filter((school) => regionNames.has(school.name) || aliases.some((alias) => school.name.startsWith(alias)));
  for (const alias of aliases) schoolCityIndex.set(alias, schools);
}

const degreeNames = { associate: "专科", undergraduate: "本科", graduate: "研究生", doctoral: "博士生" };

function recommendSchoolFormat(school, degree) {
  const normalized = school.trim().toLowerCase().replace(/[\s·•]/g, "");
  const profile = schoolProfiles.find((item) => item.keys.some((key) => normalized.includes(key.toLowerCase()))) || {
    group: "通用高校建议", style: "GB/T 7714-2015", journal: "", note: "未识别到学校专属格式，已按国内学术论文常用规范推荐。请在提交前核对学校官方模板。"
  };
  const degreeNote = degree === "associate" ? "专科毕业设计/论文模板" : `${degreeNames[degree] || degree}学位论文模板`;
  return { ...profile, school: school.trim(), degree: degreeNames[degree] || degree, degreeNote };
}

function renderSchoolRecommendation(result) {
  const target = $("#school-result");
  target.innerHTML = `<div class="result-card school-recommendation">
    <div class="result-header"><div><span class="history-type">${escapeHtml(result.group)} · ${escapeHtml(result.degree)}</span><h3>${escapeHtml(result.school)} · ${escapeHtml(result.degreeNote)}</h3></div></div>
    <p class="school-note">${escapeHtml(result.note)}</p>
    <div class="chips"><span class="chip chip-ok">推荐引用格式：${escapeHtml(result.style)}</span><span class="chip">正文排版：${escapeHtml(result.degreeNote)}</span><span class="chip">学历：${escapeHtml(result.degree)}</span></div>
    <div class="result-tools school-actions"><button class="primary-button" type="button" id="apply-school-format">用于文稿规整<span>→</span></button></div>
  </div>`;
  $("#apply-school-format").addEventListener("click", () => {
    const styleSelect = $('#format-form select[name="style"]');
    styleSelect.value = "gb7714";
    applySchoolTemplate();
  });
}

const SCHOOL_SELECTION_KEY = "academic-assistant.school-selection";

function getSchoolSelection() {
  try {
    return JSON.parse(localStorage.getItem(SCHOOL_SELECTION_KEY) || "null");
  } catch (error) {
    return null;
  }
}

function setSchoolSelection(selection) {
  if (selection) localStorage.setItem(SCHOOL_SELECTION_KEY, JSON.stringify(selection));
  else localStorage.removeItem(SCHOOL_SELECTION_KEY);
  renderFormatSchoolHint();
}

function renderFormatSchoolHint() {
  const hint = $("#format-school-hint");
  if (!hint) return;
  const selection = getSchoolSelection();
  if (selection) {
    const college = selection.college ? ` · ${escapeHtml(selection.college)}` : "";
    hint.innerHTML = `当前模板：<strong>${escapeHtml(selection.school)}</strong> · ${escapeHtml(degreeNames[selection.degree] || selection.degree)}${college} <button class="small-button" type="button" id="clear-school-template">清除</button>`;
    const clear = $("#clear-school-template");
    if (clear) {
      clear.addEventListener("click", () => {
        setSchoolSelection(null);
        showToast("已清除学校模板，导出时按引用规范排版");
      });
    }
  } else {
    hint.textContent = "未选择学校模板：导出时只应用引用规范与自定义格式，不改变正文排版。";
  }
}

async function applySchoolTemplate() {
  const form = $("#school-form");
  const selection = {
    degree: form.degree.value,
    school: form.school.value.trim(),
    college: form.college.value.trim(),
  };
  if (!selection.school) {
    form.school.focus();
    showToast("请先输入学校名称");
    return;
  }
  try {
    const response = await fetch(`/api/templates/rules?${new URLSearchParams(selection)}`);
    if (response.ok) {
      setSchoolSelection(selection);
      switchTab("format");
      showToast(`已启用 ${selection.school} 的格式模板，上传文稿即可按它排版`);
      return;
    }
    renderExtractPanel(selection);
  } catch (error) {
    showToast(error.message);
  }
}

function renderExtractPanel(selection) {
  const target = $("#template-search-results");
  target.innerHTML = `<article class="template-source key-setup">
    <div><span class="history-type">还没有该校的格式规则</span>
    <h3>上传一份 ${escapeHtml(selection.school)} · ${escapeHtml(degreeNames[selection.degree] || selection.degree)} 的 Word 模板</h3>
    <p>系统会抽取字体、字号、行距、页边距和标题格式；确认后入库，之后同一学校即可直接复用。</p>
    <div class="key-row"><input id="template-file" type="file" accept=".docx"><button class="primary-button" id="extract-template" type="button">提取格式</button></div>
    <small>仅支持 .docx；.doc 请先在 Word 中另存为 .docx。</small></div>
  </article><div id="extract-result"></div>`;
  $("#extract-template").addEventListener("click", () => runExtract(selection));
}

async function runExtract(selection) {
  const input = $("#template-file");
  const out = $("#extract-result");
  if (!input.files.length) {
    showToast("请选择一个 .docx 模板文件");
    return;
  }
  const body = new FormData();
  body.append("files", input.files[0]);
  out.innerHTML = '<div class="empty-state">正在抽取格式…</div>';
  try {
    const response = await fetch("/api/templates/extract", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "抽取失败");
    const rules = payload.rules || {};
    const meta = payload.meta || {};
    const spacing = rules.line_spacing_pt ? `${rules.line_spacing_pt} 磅` : `${rules.line_spacing || "-"} 倍`;
    const warnings = (meta.warnings || []).length
      ? `<small>提示：${escapeHtml((meta.warnings || []).join("；"))}</small>`
      : "";
    out.innerHTML = `<article class="template-source">
      <div><span class="history-type">抽取结果 · 置信度 ${Math.round((meta.confidence || 0) * 100)}%</span>
      <h3>${escapeHtml(selection.school)} 模板规则</h3>
      <p>正文 ${escapeHtml(rules.font_family || "-")} ${escapeHtml(rules.font_size || "-")} · 行距 ${escapeHtml(spacing)} · 页边距 ${escapeHtml(rules.margin_top || "-")}/${escapeHtml(rules.margin_bottom || "-")}/${escapeHtml(rules.margin_left || "-")}/${escapeHtml(rules.margin_right || "-")} cm</p>
      <small>标题字号 ${escapeHtml(rules.heading1_size || "-")} / ${escapeHtml(rules.heading2_size || "-")} / ${escapeHtml(rules.heading3_size || "-")} · 参考文献 ${escapeHtml(rules.ref_size || "-")}</small>
      ${warnings}
      <div class="actions"><button class="primary-button" id="save-template-rules" type="button">保存并启用</button></div></div>
    </article>`;
    $("#save-template-rules").addEventListener("click", () => saveTemplateRules(selection, rules, meta));
  } catch (error) {
    out.innerHTML = `<div class="warning">${escapeHtml(error.message)}</div>`;
  }
}

async function saveTemplateRules(selection, rules, meta) {
  try {
    const response = await fetch("/api/templates/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...selection,
        rules,
        confidence: meta.confidence || 0,
        source: "docx",
        verified: true,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "保存失败");
    setSchoolSelection(selection);
    switchTab("format");
    showToast("模板已保存并启用");
  } catch (error) {
    showToast(error.message);
  }
}

function updateSchoolPreview() {
  const form = $("#school-form");
  const name = form.school.value.trim();
  $("#school-result").classList.toggle("has-recommendation", Boolean(name));
  if (name) renderSchoolRecommendation(recommendSchoolFormat(name, form.degree.value));
  else $("#school-result").innerHTML = "";
}

function renderSchoolSuggestions() {
  const input = $("#school-name");
  const list = $("#school-suggestions");
  const query = input.value.trim().replace(/\s/g, "").toLowerCase();
  if (query.length < 1) {
    list.hidden = true;
    list.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
    return;
  }
  const degree = $("#school-form").degree.value;
  const cityMatches = [...schoolCityIndex.entries()]
    .filter(([alias]) => query.includes(alias.toLowerCase()))
    .flatMap(([, schools]) => schools);
  const matches = [...new Map([...schoolCatalog, ...cityMatches]
    .filter((school) => school.levels.includes(degree) && (school.name.toLowerCase().includes(query) || [...schoolCityIndex.keys()].some((alias) => query.includes(alias.toLowerCase()) && schoolCityIndex.get(alias).includes(school))))
    .map((school) => [school.name, school])).values()]
    .map((school) => school.name)
    .slice(0, 10);
  if (!matches.length) {
    list.hidden = true;
    list.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
    return;
  }
  list.innerHTML = matches.map((name, index) => `<button type="button" class="school-suggestion${index === 0 ? " active" : ""}" role="option" aria-selected="${index === 0}" data-school="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("");
  list.hidden = false;
  input.setAttribute("aria-expanded", "true");
}

$("#school-suggestions").addEventListener("mousedown", (event) => {
  const option = event.target.closest("[data-school]");
  if (!option) return;
  event.preventDefault();
  const input = $("#school-name");
  input.value = option.dataset.school;
  $("#school-suggestions").hidden = true;
  input.setAttribute("aria-expanded", "false");
  updateSchoolPreview();
});

$("#school-name").addEventListener("input", () => {
  renderSchoolSuggestions();
  updateSchoolPreview();
});
$("#school-name").addEventListener("focus", renderSchoolSuggestions);
$("#school-name").addEventListener("keydown", (event) => {
  const list = $("#school-suggestions");
  if (list.hidden) return;
  const options = [...list.querySelectorAll("[data-school]")];
  let index = options.findIndex((item) => item.classList.contains("active"));
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    index = (index + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
    options.forEach((item, i) => {
      item.classList.toggle("active", i === index);
      item.setAttribute("aria-selected", String(i === index));
    });
  } else if (event.key === "Enter" && options.length) {
    event.preventDefault();
    options[Math.max(index, 0)].click();
  } else if (event.key === "Escape") {
    list.hidden = true;
    event.currentTarget.setAttribute("aria-expanded", "false");
  }
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".school-autocomplete-field")) {
    $("#school-suggestions").hidden = true;
    $("#school-name").setAttribute("aria-expanded", "false");
  }
});

$("#school-form").degree.addEventListener("change", () => {
  renderSchoolSuggestions();
  updateSchoolPreview();
});
$("#school-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!event.currentTarget.school.value.trim()) {
    event.currentTarget.school.focus();
    showToast("请先输入学校名称");
    return;
  }
  updateSchoolPreview();
});

const CONFIDENCE_LABELS = { high: "高相关", medium: "中等相关", low: "参考" };

function renderCustomStyleShortcut(target) {
  target.innerHTML += `<div class="actions"><button class="small-button" id="go-custom-style">用自定义格式继续（02 自定义格式）</button></div>`;
  $("#go-custom-style").addEventListener("click", () => {
    switchTab("journals");
    showToast("在 02 自定义格式里创建或选择自定义格式");
  });
}

function renderSearchUnavailable(target) {
  target.innerHTML = `<div class="empty-state">检索服务未启用。<br>部署者需在启动前设置环境变量 <code>TAVILY_API_KEY</code>，重启后即可联网检索。<br>也可以先用 02 自定义格式里的排版继续。</div>`;
  renderCustomStyleShortcut(target);
}

function renderTemplateResults(data, target) {
  if (!data.configured) {
    renderSearchUnavailable(target);
    return;
  }
  const results = data.results || [];
  const notice = `<p class="template-search-notice">${escapeHtml(data.message || "")}${data.cached ? "（来自本地缓存）" : ""}</p>`;
  if (!results.length) {
    target.innerHTML = `${notice}<div class="empty-state">没有找到学校/学院的官方模板候选。<br>可以补充学院全称、换个说法重试，或直接用自定义格式。</div>`;
    renderCustomStyleShortcut(target);
    target.innerHTML += `<div class="actions"><button class="small-button" id="retry-template-search">重新检索</button></div>`;
    $("#retry-template-search").addEventListener("click", () => runTemplateSearch(true));
    return;
  }
  const cards = results.map((item) => `<article class="template-source">
    <div><span class="history-type">${item.official_domain_hint ? "教育机构域名" : "网页候选"} · ${escapeHtml(item.domain)}</span>
    <h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
    <p>${escapeHtml(item.snippet || "无摘要")}</p>
    <small>${item.published_date ? `网页日期：${escapeHtml(item.published_date)} · ` : ""}${CONFIDENCE_LABELS[item.confidence] || "参考"} · ${escapeHtml(item.status || "待人工核验")}</small></div>
  </article>`).join("");
  target.innerHTML = notice + cards;
  target.innerHTML += `<div class="actions"><button class="small-button" id="use-school-template">使用该学校模板排版</button></div>`;
  $("#use-school-template").addEventListener("click", () => applySchoolTemplate());
  renderCustomStyleShortcut(target);
}

async function runTemplateSearch(refresh = false) {
  const form = $("#school-form");
  const school = form.school.value.trim();
  const target = $("#template-search-results");
  if (!school) {
    form.school.focus();
    showToast("请先输入学校名称");
    return;
  }
  target.innerHTML = '<div class="empty-state">正在检索模板来源…</div>';
  const params = new URLSearchParams({ degree: form.degree.value, school, college: form.college.value.trim() });
  if (refresh) params.set("refresh", "1");
  try {
    const response = await fetch(`/api/templates/search?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "模板搜索失败");
    renderTemplateResults(data, target);
  } catch (error) {
    target.innerHTML = `<div class="warning">${escapeHtml(error.message)}</div>`;
  }
}

$("#search-school-templates").addEventListener("click", () => runTemplateSearch(false));

async function submitForm(form, endpoint, resultSelector) {
  const files = form.querySelector('input[type="file"]').files;
  if (!files.length) {
    showToast("请先选择文件");
    return;
  }
  const legacyDoc = [...files].find((file) => file.name.toLowerCase().endsWith(".doc"));
  if (legacyDoc) {
    showToast(`暂不支持 .doc（${legacyDoc.name}），请先在 Word 中另存为 .docx`);
    return;
  }
  const result = $(resultSelector);
  result.innerHTML = '<div class="empty-state">正在分析文稿，请稍候...</div>';
  const data = new FormData(form);
  if (endpoint.includes("/api/format")) {
    const selection = getSchoolSelection();
    if (selection) {
      data.append("school_degree", selection.degree);
      data.append("school_name", selection.school);
      data.append("school_college", selection.college || "");
    }
  }
  try {
    const response = await fetch(endpoint, { method: "POST", body: data });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "处理失败");
    endpoint.includes("format") ? renderFormat(payload, result) : renderReview(payload, result);
    showToast("处理完成，结果已保存到本地记录");
  } catch (error) {
    result.innerHTML = `<div class="warning">${escapeHtml(error.message)}</div>`;
    showToast(error.message);
  }
}

function renderExportButtons(id, kind) {
  const buttons = [
    `<a class="small-button" href="/api/download/${id}?format=docx">Word</a>`,
    `<a class="small-button" href="/api/download/${id}?format=md">Markdown</a>`,
  ];
  if (kind === "format") {
    buttons.push(
      `<div class="export-dropdown">` +
      `<button class="small-button" onclick="toggleDropdown(this)">导出参考文献 ▾</button>` +
      `<div class="dropdown-menu">` +
      `<a href="/api/download/${id}?format=bibtex">BibTeX (.bib)</a>` +
      `<a href="/api/download/${id}?format=ris">RIS (.ris)</a>` +
      `<a href="/api/download/${id}?format=endnote">EndNote (.enw)</a>` +
      `<a href="/api/download/${id}?format=txt">纯文本 (.txt)</a>` +
      `</div></div>`
    );
  }
  return buttons.join("");
}

function toggleDropdown(btn) {
  const menu = btn.nextElementSibling;
  document.querySelectorAll(".dropdown-menu").forEach((m) => { if (m !== menu) m.classList.remove("show"); });
  menu.classList.toggle("show");
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".export-dropdown")) {
    document.querySelectorAll(".dropdown-menu").forEach((m) => m.classList.remove("show"));
  }
});

function renderStructure(structure) {
  if (!structure || !structure.sections) return "";
  const sections = structure.sections.map((s) => `<span class="chip chip-ok">${escapeHtml(s.label)}</span>`).join("");
  const missing = (structure.missing_sections || []).map((s) => `<span class="chip chip-warn">缺失：${escapeHtml(s)}</span>`).join("");
  return `<div class="structure-info"><p class="meta-label">文档结构</p><div class="chips">${sections}${missing}</div></div>`;
}

function renderFormat(data, target) {
  const warnings = (data.warnings || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  const structure = renderStructure(data.structure);
  const overridesChip = data.journal_base && data.journal_overrides
    ? `<span class="chip">继承 ${escapeHtml(data.journal_base.school)} · 微调 ${countStyleLeaves(data.journal_overrides)} 项</span>`
    : "";
  const schoolTemplate = data.school_template
    ? `<div class="chips"><span class="chip chip-ok">已按 ${escapeHtml(data.school_template.school)} · ${escapeHtml(degreeNames[data.school_template.degree] || data.school_template.degree)} 模板排版</span><span class="chip">模板置信度 ${Math.round((data.school_template.confidence || 0) * 100)}%</span>${overridesChip}</div>`
    : (overridesChip ? `<div class="chips">${overridesChip}</div>` : "");
  const preserveBtn = data.preserve_available
    ? `<a class="small-button" href="/api/download/${data.id}?format=docx&mode=preserve">保留原稿 Word</a>`
    : "";
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${escapeHtml(data.style)} · ${escapeHtml(data.source_name)}</p></div>
        <div class="result-tools">${renderExportButtons(data.id, "format")}${preserveBtn}</div>
      </div>
      <div class="metrics">
        <div class="metric"><strong>${data.paragraph_count}</strong><span>段落</span></div>
        <div class="metric"><strong>${data.reference_count}</strong><span>条参考文献</span></div>
        <div class="metric"><strong>${data.character_count}</strong><span>字符</span></div>
      </div>
      ${schoolTemplate}
      ${structure}
      ${warnings}
      <div class="result-text">${escapeHtml(data.formatted_text)}</div>
    </div>`;
}

function renderCards(cards) {
  if (!cards || !cards.length) return "";
  const cardHtml = cards.map((card) => `
    <div class="literature-card">
      <div class="card-header"><span class="card-index">#${card.index}</span><strong>${escapeHtml(card.title)}</strong><span class="card-year">${escapeHtml(card.year)}</span></div>
      <div class="card-keywords">${(card.keywords || []).map((k) => `<span class="chip">${escapeHtml(k)}</span>`).join("")}</div>
      <div class="card-fields">
        ${renderCardField("研究问题", card.research_question)}
        ${renderCardField("研究方法", card.method)}
        ${renderCardField("数据集", card.dataset)}
        ${renderCardField("主要结论", card.conclusion)}
        ${renderCardField("创新点", card.innovation)}
        ${renderCardField("局限性", card.limitation)}
      </div>
    </div>`).join("");
  return `<div class="cards-section"><p class="meta-label">文献分析卡片</p>${cardHtml}</div>`;
}

function renderCardField(label, value) {
  if (!value || value === "未提取") return "";
  return `<div class="card-field"><span class="field-label">${escapeHtml(label)}</span><span class="field-value">${escapeHtml(value)}</span></div>`;
}

function renderComparisons(comparisons) {
  if (!comparisons || !comparisons.length) return "";
  const items = comparisons.map((cmp) => `
    <div class="comparison-item">
      <span class="cmp-source">文献 ${cmp.source_a} ↔ 文献 ${cmp.source_b}</span>
      <span class="cmp-relation">${escapeHtml(cmp.relation)}</span>
      ${cmp.shared_keywords.length ? `<span class="cmp-keywords">共同：${cmp.shared_keywords.map((k) => escapeHtml(k)).join("、")}</span>` : ""}
    </div>`).join("");
  return `<div class="comparisons-section"><p class="meta-label">观点比较与来源追踪</p>${items}</div>`;
}

function renderLlmStatus(status) {
  if (!status) return "";
  const configured = status.configured ? "已配置" : "未配置";
  const model = status.model || "无";
  const notice = status.privacy_notice ? `<div class="warning">${escapeHtml(status.privacy_notice)}</div>` : "";
  const elapsed = status.elapsed_seconds != null ? ` · 耗时 ${status.elapsed_seconds}s` : "";
  const stat = status.status ? ` · ${escapeHtml(status.status)}` : "";
  const err = status.error ? `<div class="warning">大模型调用失败：${escapeHtml(status.error)}</div>` : "";
  return `<div class="llm-status"><p class="meta-label">大模型状态</p><p>模型：${escapeHtml(model)} · ${configured}${elapsed}${stat}</p>${notice}${err}</div>`;
}

function renderReview(data, target) {
  const chips = (data.keywords || []).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  const skipped = (data.skipped || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  const cards = renderCards(data.cards);
  const comparisons = renderComparisons(data.comparisons);
  const llmStatus = renderLlmStatus(data.llm_status);
  const engineLabel = data.engine === "llm-enhanced" ? "大模型增强模式" : data.engine === "user-edited" ? "用户编辑版" : "本地规则引擎";
  const editBtn = `<button class="small-button" onclick="toggleEdit(${data.id})">编辑综述</button>`;
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${engineLabel} · ${data.item_count} 篇文献</p></div>
        <div class="result-tools">${renderExportButtons(data.id, "review")}${editBtn}</div>
      </div>
      ${llmStatus}
      <div class="chips">${chips}</div>
      ${skipped}
      ${cards}
      ${comparisons}
      <div id="review-edit-area" style="display:none;">
        <textarea id="review-edit-text" class="edit-textarea">${escapeHtml(data.markdown)}</textarea>
        <button class="small-button" onclick="saveEdit(${data.id})">保存编辑</button>
      </div>
      <div class="result-text" id="review-markdown">${escapeHtml(data.markdown)}</div>
    </div>`;
}

function toggleEdit(id) {
  const area = $("#review-edit-area");
  const markdown = $("#review-markdown");
  if (area.style.display === "none") {
    area.style.display = "block";
    markdown.style.display = "none";
  } else {
    area.style.display = "none";
    markdown.style.display = "block";
  }
}

async function saveEdit(id) {
  const text = $("#review-edit-text").value;
  if (!text.trim()) {
    showToast("内容不能为空");
    return;
  }
  const formData = new FormData();
  formData.append("job_id", id);
  formData.append("markdown", text);
  try {
    const response = await fetch("/api/review/edit", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "保存失败");
    renderReview(payload, $("#review-result"));
    showToast("编辑已保存");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadHistory() {
  const target = $("#history-list");
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!data.items.length) {
      target.innerHTML = '<div class="empty-state">还没有处理记录。完成一次文稿规整或综述生成后，结果会出现在这里。</div>';
      return;
    }
    target.innerHTML = data.items.map((item) => {
      const payload = item.payload || {};
      const isFormat = item.kind === "format";
      const citationStyle = payload.citation_style_label ||
        ({ gb7714: "GB/T 7714-2015", apa7: "APA 7", ieee: "IEEE" }[payload.citation_style]) ||
        (payload.style && !payload.journal_style_id ? payload.style : "基础规范未记录");
      const journalStyle = payload.journal_style_name || payload.journal_rules && payload.style;
      const formatTag = isFormat
        ? `<span class="chip chip-ok">${escapeHtml(journalStyle ? `${journalStyle}（基础规范：${citationStyle}）` : citationStyle)}</span>`
        : "";
      return `
      <div class="history-item">
        <div><span class="history-type">${isFormat ? "文稿规整" : "综述生成"}</span>${formatTag}<h3>${escapeHtml(item.title)}</h3><p>${new Date(item.created_at).toLocaleString("zh-CN")}</p></div>
        <div>${renderExportButtons(item.id, item.kind)}</div>
      </div>`;
    }).join("");
  } catch {
    target.innerHTML = '<div class="warning">历史记录读取失败，请检查服务是否仍在运行。</div>';
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
}

activateTabs();
setupDropzone("#format-dropzone", '#format-form input[type="file"]', "#format-file-name");
setupDropzone("#review-dropzone", '#review-form input[type="file"]', "#review-file-name");
$("#format-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/api/format", "#format-result");
});
$("#review-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/api/review", "#review-result");
});
$("#refresh-history").addEventListener("click", loadHistory);
loadHistory();

let authToken = null;
let currentUser = null;

function getAuthHeaders() {
  const headers = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  return headers;
}

async function checkAuth() {
  try {
    const response = await fetch("/api/auth/me");
    const data = await response.json();
    if (data.user_id) {
      currentUser = data;
      updateUserUI();
    }
  } catch {}
}

function updateUserUI() {
  if (currentUser) {
    $("#auth-area").style.display = "none";
    $("#user-area").style.display = "inline";
    $("#user-display").textContent = `${currentUser.username}（${currentUser.role === "teacher" ? "教师" : "学生"}）`;
  } else {
    $("#auth-area").style.display = "inline";
    $("#user-area").style.display = "none";
    $("#user-display").textContent = "";
  }
}

function showAuthModal(mode) {
  const modal = $("#auth-modal");
  const title = $("#auth-modal-title");
  const roleField = $("#role-field");
  const submitBtn = $("#auth-submit-btn");
  modal.style.display = "flex";
  if (mode === "register") {
    title.textContent = "注册";
    roleField.style.display = "block";
    submitBtn.textContent = "注册";
  } else {
    title.textContent = "登录";
    roleField.style.display = "none";
    submitBtn.textContent = "登录";
  }
  modal.dataset.mode = mode;
}

function closeAuthModal() {
  $("#auth-modal").style.display = "none";
  $("#auth-form").reset();
}

$("#show-login-btn").addEventListener("click", () => showAuthModal("login"));
$("#show-register-btn").addEventListener("click", () => showAuthModal("register"));
$("#close-auth-modal").addEventListener("click", closeAuthModal);
$("#logout-btn").addEventListener("click", async () => {
  try {
    await fetch("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() } });
  } catch {}
  authToken = null;
  currentUser = null;
  updateUserUI();
  showToast("已登出");
});

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const mode = $("#auth-modal").dataset.mode;
  const data = {
    username: form.username.value.trim(),
    password: form.password.value,
  };
  if (mode === "register") data.role = form.role.value;
  try {
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "操作失败");
    authToken = payload.token;
    currentUser = { user_id: payload.user_id, username: payload.username, role: payload.role };
    updateUserUI();
    closeAuthModal();
    showToast(`${mode === "register" ? "注册" : "登录"}成功`);
  } catch (error) {
    showToast(error.message);
  }
});

async function loadJournalStyles() {
  const target = $("#journal-list");
  try {
    const response = await fetch("/api/journal-styles");
    const data = await response.json();
    if (!data.styles.length) {
      target.innerHTML = '<div class="empty-state">暂无自定义格式。</div>';
      return;
    }
    const builtin = data.styles.filter((s) => s.is_builtin);
    const custom = data.styles.filter((s) => !s.is_builtin);
    let html = "";
    if (builtin.length) {
      html += `<div class="journal-builtin"><p class="meta-label">内置格式（${builtin.length}）</p><div class="chips">` +
        builtin.map((s) => `<span class="chip chip-ok" title="${escapeHtml(s.publisher || "")}">${escapeHtml(s.name)}</span>`).join("") +
        `</div></div>`;
    }
    if (custom.length) {
      html += `<div class="journal-custom"><p class="meta-label">自定义格式</p>` +
        custom.map((s) => `
          <div class="history-item">
            <div><span class="history-type">自定义</span><h3>${escapeHtml(s.name)}</h3><p>${escapeHtml(s.publisher || "未指定")}</p></div>
            <div><button class="small-button" onclick="deleteJournalStyle(${s.id})">删除</button></div>
          </div>`).join("") +
        `</div>`;
    }
    target.innerHTML = html;
  } catch {
    target.innerHTML = '<div class="warning">自定义格式加载失败。</div>';
  }
}

async function deleteJournalStyle(id) {
  try {
    const response = await fetch(`/api/journal-styles/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "删除失败");
    }
    showToast("已删除");
    loadJournalStyles();
  } catch (error) {
    showToast(error.message);
  }
}

function setStylePath(tree, path, value) {
  let node = tree;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    if (!node[key] || typeof node[key] !== "object") node[key] = {};
    node = node[key];
  }
  node[path[path.length - 1]] = value;
}

function buildStyleRules(form) {
  const data = new FormData(form);
  const rules = { schema_version: 2 };
  for (const [key, value] of data.entries()) {
    if (key === "name" || key === "publisher") continue;
    if (value === "") continue;
    setStylePath(rules, key.split("."), value);
  }
  ["1", "2", "3"].forEach((level) => {
    const existing = (rules.headings && rules.headings[level]) || {};
    existing.bold = data.has(`headings.${level}.bold`);
    setStylePath(rules, ["headings", level], existing);
  });
  return rules;
}

const STYLE_BASE = { info: null, flat: null, rules: null };

function setFormValue(form, name, value) {
  const field = form.elements[name];
  if (!field) return;
  const text = String(value);
  if (field.tagName === "SELECT") {
    if (![...field.options].some((option) => option.value === text)) {
      const option = document.createElement("option");
      option.value = text;
      option.textContent = text;
      field.appendChild(option);
    }
    field.value = text;
  } else if (field.type === "checkbox") {
    field.checked = Boolean(value);
  } else {
    field.value = text;
  }
}

function fillStyleFromFlat(form, flat) {
  const direct = {
    "page.margins.top": "margin_top",
    "page.margins.bottom": "margin_bottom",
    "page.margins.left": "margin_left",
    "page.margins.right": "margin_right",
    "body.font_cn": "font_family",
    "body.size": "font_size",
    "body.alignment": "body_alignment",
    "references.font_cn": "ref_font",
    "references.size": "ref_size",
    "references.numbering": "ref_numbering",
    "references.hanging_indent": "ref_hanging_chars",
    "header_footer.header_text": "page_header",
    "header_footer.page_number.position": "page_number_pos",
    "captions.figure.position": "figure_caption",
    "captions.figure.size": "caption_size",
  };
  for (const [field, key] of Object.entries(direct)) {
    if (flat[key] !== undefined && flat[key] !== "") setFormValue(form, field, flat[key]);
  }
  if (flat.line_spacing_pt) {
    setFormValue(form, "body.line_spacing.type", "exact");
    setFormValue(form, "body.line_spacing.value", flat.line_spacing_pt);
  } else if (flat.line_spacing) {
    setFormValue(form, "body.line_spacing.type", "multiple");
    setFormValue(form, "body.line_spacing.value", flat.line_spacing);
  }
  if (flat.first_line_indent) {
    setFormValue(form, "body.first_line_indent.chars", flat.first_line_indent === "2chars" ? 2 : 0);
  }
  [1, 2, 3].forEach((level) => {
    if (flat[`heading${level}_font`]) setFormValue(form, `headings.${level}.font_cn`, flat[`heading${level}_font`]);
    if (flat[`heading${level}_size`]) setFormValue(form, `headings.${level}.size`, flat[`heading${level}_size`]);
    if (flat[`heading${level}_align`]) setFormValue(form, `headings.${level}.align`, flat[`heading${level}_align`]);
    if (flat[`heading${level}_bold`] !== undefined) setFormValue(form, `headings.${level}.bold`, flat[`heading${level}_bold`]);
    if (flat[`heading${level}_before`]) setFormValue(form, `headings.${level}.before`, flat[`heading${level}_before`] / 20);
    if (flat[`heading${level}_after`]) setFormValue(form, `headings.${level}.after`, flat[`heading${level}_after`] / 20);
  });
}

function diffStyleRules(base, current) {
  const output = {};
  const baseNode = base || {};
  for (const [key, value] of Object.entries(current || {})) {
    if (key === "schema_version") continue;
    const previous = baseNode[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const child = diffStyleRules(previous || {}, value);
      if (Object.keys(child).length) output[key] = child;
    } else if (value !== previous) {
      output[key] = value;
    }
  }
  return output;
}

function countStyleLeaves(node) {
  let total = 0;
  const stack = [node || {}];
  while (stack.length) {
    const current = stack.pop();
    for (const value of Object.values(current)) {
      if (value && typeof value === "object") stack.push(value);
      else total += 1;
    }
  }
  return total;
}

function updateBaseStatus() {
  const status = $("#base-status");
  const form = $("#journal-style-form");
  if (!status || !form) return;
  if (!STYLE_BASE.info || !STYLE_BASE.rules) {
    status.textContent = "未继承学校模板：将作为独立格式保存。";
    return;
  }
  const current = buildStyleRules(form);
  const count = countStyleLeaves(diffStyleRules(STYLE_BASE.rules, current));
  const degree = degreeNames[STYLE_BASE.info.degree] || STYLE_BASE.info.degree;
  status.textContent = `基于 ${STYLE_BASE.info.school} · ${degree}，已改 ${count} 项`;
}

async function checkBackendCompat() {
  try {
    const response = await fetch("/api/settings/tavily");
    if (response.status === 404) {
      showOutdatedBackendBanner();
    }
  } catch (error) {
    /* 服务不可达时由各功能自身报错 */
  }
}

function showOutdatedBackendBanner() {
  if (document.getElementById("backend-outdated")) return;
  const bar = document.createElement("div");
  bar.id = "backend-outdated";
  bar.className = "backend-outdated";
  bar.innerHTML = `当前页面连接的是 <b>旧版后端</b>：缺少学校模板、格式继承与搜索接口。<a class="backend-outdated-link" href="//${location.hostname}:8766/">点此打开新版（8766）</a>，或重启服务后刷新。`;
  document.body.prepend(bar);
}

async function loadBaseTemplate() {
  const degree = $("#base-degree").value;
  const school = $("#base-school").value.trim();
  const college = $("#base-college").value.trim();
  if (!school) {
    showToast("请填写要继承的学校");
    return;
  }
  try {
    const response = await fetch(`/api/templates/rules?${new URLSearchParams({ degree, school, college })}`);
    const payload = await response.json();
    if (!response.ok) {
      if (payload.error === "接口不存在") {
        throw new Error("当前后端是旧版本：请改用新版端口或重启服务");
      }
      throw new Error(payload.error || "没有找到该校模板，请先到 01 学校格式推荐提取。");
    }
    const form = $("#journal-style-form");
    fillStyleFromFlat(form, payload.rules || {});
    STYLE_BASE.info = { degree, school, college };
    STYLE_BASE.flat = payload.rules || {};
    STYLE_BASE.rules = buildStyleRules(form);
    $("#reset-base-template").hidden = false;
    updateStylePreview();
    updateBaseStatus();
    showToast(`已载入 ${school} 的模板，可在其上微调`);
  } catch (error) {
    showToast(error.message);
  }
}

function resetBaseTemplate() {
  if (!STYLE_BASE.flat) return;
  const form = $("#journal-style-form");
  fillStyleFromFlat(form, STYLE_BASE.flat);
  STYLE_BASE.rules = buildStyleRules(form);
  updateStylePreview();
  updateBaseStatus();
}

const FONT_CSS = {
  SimSun: '"SimSun","宋体",serif',
  SimHei: '"SimHei","黑体",sans-serif',
  KaiTi: '"KaiTi","楷体",serif',
  FangSong: '"FangSong","仿宋",serif',
  "Times New Roman": '"Times New Roman",serif',
  Calibri: "Calibri,sans-serif",
  Arial: "Arial,sans-serif",
};

function updateStylePreview() {
  const form = $("#journal-style-form");
  const page = $("#style-preview-page");
  if (!form || !page) return;
  const value = (name, fallback) => (form.elements[name] && form.elements[name].value) || fallback;
  const padding = (cm) => `${Math.max(4, Math.round(Number(cm || 2.54) * 9))}px`;
  page.style.padding = `${padding(value("page.margins.top", 2.54))} ${padding(value("page.margins.right", 3.18))} ${padding(value("page.margins.bottom", 2.54))} ${padding(value("page.margins.left", 3.18))}`;

  page.querySelectorAll(".preview-body").forEach((node) => {
    node.style.fontFamily = FONT_CSS[value("body.font_cn", "SimSun")] || "serif";
    node.style.fontSize = value("body.size", "12pt");
    const type = value("body.line_spacing.type", "multiple");
    const spacing = value("body.line_spacing.value", "1.5");
    node.style.lineHeight = type === "exact" ? `${spacing}pt` : String(spacing);
    node.style.textIndent = `${Number(value("body.first_line_indent.chars", 2)) || 0}em`;
    node.style.textAlign = value("body.alignment", "both") === "both" ? "justify" : "left";
    node.style.marginTop = `${Number(value("body.space_before", 0)) || 0}pt`;
    node.style.marginBottom = `${Number(value("body.space_after", 0)) || 0}pt`;
  });

  const h1 = page.querySelector(".preview-h1");
  if (h1) {
    h1.style.fontFamily = FONT_CSS[value("headings.1.font_cn", "SimHei")] || "sans-serif";
    h1.style.fontSize = value("headings.1.size", "22pt");
    h1.style.textAlign = value("headings.1.align", "center");
    h1.style.fontWeight = form.elements["headings.1.bold"] && form.elements["headings.1.bold"].checked ? "700" : "400";
  }
  const h2 = page.querySelector(".preview-h2");
  if (h2) {
    h2.style.fontFamily = FONT_CSS[value("headings.2.font_cn", "SimHei")] || "sans-serif";
    h2.style.fontSize = value("headings.2.size", "16pt");
    h2.style.textAlign = value("headings.2.align", "left");
    h2.style.fontWeight = form.elements["headings.2.bold"] && form.elements["headings.2.bold"].checked ? "700" : "400";
  }
  const caption = page.querySelector(".preview-caption");
  if (caption) {
    caption.style.fontSize = value("captions.figure.size", "10.5pt");
    caption.style.textAlign = value("captions.figure.align", "center");
    caption.style.fontFamily = FONT_CSS[value("body.font_cn", "SimSun")] || "serif";
  }
  const ref = page.querySelector(".preview-ref");
  if (ref) {
    ref.style.fontSize = value("references.size", "10.5pt");
    ref.style.fontFamily = FONT_CSS[value("references.font_cn", "SimSun")] || "serif";
  }
  updateBaseStatus();
}

$("#journal-style-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const rules = buildStyleRules(form);
  try {
    const response = await fetch("/api/journal-styles", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({
        name: form.elements["name"].value,
        publisher: form.elements["publisher"].value,
        rules,
        base: STYLE_BASE.info,
        overrides: STYLE_BASE.info ? diffStyleRules(STYLE_BASE.rules, rules) : undefined,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "创建失败");
    showToast("自定义格式已保存");
    loadJournalStyles();
    loadFormatJournalStyles();
    updateStylePreview();
  } catch (error) {
    showToast(error.message);
  }
});

$("#journal-style-form").addEventListener("input", updateStylePreview);
$("#journal-style-form").addEventListener("change", updateStylePreview);
$("#load-base-template").addEventListener("click", loadBaseTemplate);
$("#reset-base-template").addEventListener("click", resetBaseTemplate);

async function loadFormatJournalStyles() {
  const select = $("#format-journal-style");
  if (!select) return;
  try {
    const response = await fetch("/api/journal-styles");
    const data = await response.json();
    const current = select.value;
    select.innerHTML = '<option value="">不使用</option>' +
      data.styles.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}${s.is_builtin ? "" : "（自定义）"}</option>`).join("");
    select.value = current;
  } catch {}
}

function renderStatsChart(points) {
  const target = $("#stats-chart");
  if (!target) return;
  if (!points || !points.length) {
    target.innerHTML = '<div class="empty-state">暂无趋势数据。</div>';
    return;
  }
  const width = 760;
  const height = 220;
  const pad = { top: 18, right: 16, bottom: 30, left: 44 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const max = Math.max(1, ...points.map((point) => point.count));
  const stepX = points.length > 1 ? innerW / (points.length - 1) : innerW;
  const coords = points.map((point, index) => [
    pad.left + index * stepX,
    pad.top + innerH - (point.count / max) * innerH,
  ]);
  const line = coords.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(1)},${pad.top + innerH} L${coords[0][0].toFixed(1)},${pad.top + innerH} Z`;
  const grid = [0, 0.5, 1].map((ratio) => {
    const y = pad.top + innerH - ratio * innerH;
    const value = Math.round(ratio * max);
    return `<line x1="${pad.left}" y1="${y.toFixed(1)}" x2="${width - pad.right}" y2="${y.toFixed(1)}" stroke="#e6eeee" stroke-width="1"/>`
      + `<text x="${pad.left - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" class="chart-axis">${value}</text>`;
  }).join("");
  const dots = coords.map(([x, y], index) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="#0f766e"><title>${points[index].date}: ${points[index].count} 次</title></circle>`).join("");
  const labels = points.map((point, index) => {
    if (index % 2 !== 0 && index !== points.length - 1) return "";
    return `<text x="${coords[index][0].toFixed(1)}" y="${height - 8}" text-anchor="middle" class="chart-axis">${point.date}</text>`;
  }).join("");
  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="近 14 天处理次数折线图">
    ${grid}
    <path d="${area}" fill="#0f766e" fill-opacity="0.08"/>
    <path d="${line}" fill="none" stroke="#0f766e" stroke-width="2"/>
    ${dots}
    ${labels}
  </svg>`;
}

async function loadStats() {
  const target = $("#stats-content");
  try {
    const response = await fetch("/api/stats", { headers: getAuthHeaders() });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "加载失败");
    renderStatsChart(data.daily_counts || []);
    const styleDist = Object.entries(data.style_distribution || {}).map(([k, v]) => `<span class="chip">${escapeHtml(k)}: ${v}</span>`).join("");
    target.innerHTML = `
      <div class="metrics">
        <div class="metric"><strong>${data.total_jobs}</strong><span>总处理量</span></div>
        <div class="metric"><strong>${data.format_jobs}</strong><span>文稿规整</span></div>
        <div class="metric"><strong>${data.review_jobs}</strong><span>综述生成</span></div>
        <div class="metric"><strong>${data.recent_day}</strong><span>近 24 小时</span></div>
        <div class="metric"><strong>${data.recent_week}</strong><span>近 7 天</span></div>
        <div class="metric"><strong>${data.total_references}</strong><span>参考文献总数</span></div>
        <div class="metric"><strong>${data.total_warnings}</strong><span>纠错警告</span></div>
        <div class="metric"><strong>${data.duplicate_warnings}</strong><span>重复引用</span></div>
      </div>
      <div class="result-card" style="margin-top:1rem;">
        <p class="meta-label">引用规范分布</p>
        <div class="chips">${styleDist || "暂无数据"}</div>
        <p class="meta-label" style="margin-top:1rem;">大模型调用</p>
        <p>调用次数：${data.llm_calls} · 失败：${data.llm_failures} · 成功率：${data.llm_success_rate}% · 平均耗时：${data.avg_llm_elapsed_seconds}s</p>
      </div>`;
  } catch (error) {
    target.innerHTML = `<div class="warning">${escapeHtml(error.message)}</div>`;
  }
}

checkAuth();
checkBackendCompat();
loadFormatJournalStyles();
renderFormatSchoolHint();
