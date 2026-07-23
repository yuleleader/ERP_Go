// 国家名称匹配数据库
export const countryDatabase = {
  // 中文名称
  '中国': { code: 'CN', name: 'China', aliases: ['中华人民共和国', '华夏', '天朝'] },
  '美国': { code: 'US', name: 'United States', aliases: ['美利坚合众国', 'USA', 'United States of America'] },
  '日本': { code: 'JP', name: 'Japan', aliases: ['日本国', 'Nippon'] },
  '韩国': { code: 'KR', name: 'South Korea', aliases: ['大韩民国', 'Republic of Korea'] },
  '英国': { code: 'GB', name: 'United Kingdom', aliases: ['大不列颠', 'UK', 'United Kingdom of Great Britain'] },
  '法国': { code: 'FR', name: 'France', aliases: ['法兰西', 'French Republic'] },
  '德国': { code: 'DE', name: 'Germany', aliases: ['德意志', 'Federal Republic of Germany'] },
  '意大利': { code: 'IT', name: 'Italy', aliases: ['意大利共和国'] },
  '西班牙': { code: 'ES', name: 'Spain', aliases: ['西班牙王国'] },
  '葡萄牙': { code: 'PT', name: 'Portugal', aliases: ['葡萄牙共和国'] },
  '荷兰': { code: 'NL', name: 'Netherlands', aliases: ['尼德兰', 'Holland'] },
  '比利时': { code: 'BE', name: 'Belgium', aliases: ['比利时王国'] },
  '卢森堡': { code: 'LU', name: 'Luxembourg', aliases: ['卢森堡大公国'] },
  '瑞士': { code: 'CH', name: 'Switzerland', aliases: ['瑞士联邦'] },
  '奥地利': { code: 'AT', name: 'Austria', aliases: ['奥地利共和国'] },
  '瑞典': { code: 'SE', name: 'Sweden', aliases: ['瑞典王国'] },
  '挪威': { code: 'NO', name: 'Norway', aliases: ['挪威王国'] },
  '丹麦': { code: 'DK', name: 'Denmark', aliases: ['丹麦王国'] },
  '芬兰': { code: 'FI', name: 'Finland', aliases: ['芬兰共和国'] },
  '冰岛': { code: 'IS', name: 'Iceland', aliases: ['冰岛共和国'] },
  '爱尔兰': { code: 'IE', name: 'Ireland', aliases: ['爱尔兰共和国'] },
  '波兰': { code: 'PL', name: 'Poland', aliases: ['波兰共和国'] },
  '捷克': { code: 'CZ', name: 'Czech Republic', aliases: ['捷克共和国'] },
  '斯洛伐克': { code: 'SK', name: 'Slovakia', aliases: ['斯洛伐克共和国'] },
  '匈牙利': { code: 'HU', name: 'Hungary', aliases: ['匈牙利共和国'] },
  '斯洛文尼亚': { code: 'SI', name: 'Slovenia', aliases: ['斯洛文尼亚共和国'] },
  '克罗地亚': { code: 'HR', name: 'Croatia', aliases: ['克罗地亚共和国'] },
  '塞尔维亚': { code: 'RS', name: 'Serbia', aliases: ['塞尔维亚共和国'] },
  '保加利亚': { code: 'BG', name: 'Bulgaria', aliases: ['保加利亚共和国'] },
  '罗马尼亚': { code: 'RO', name: 'Romania', aliases: ['罗马尼亚'] },
  '希腊': { code: 'GR', name: 'Greece', aliases: ['希腊共和国', 'Hellenic Republic'] },
  '土耳其': { code: 'TR', name: 'Turkey', aliases: ['土耳其共和国'] },
  '俄罗斯': { code: 'RU', name: 'Russia', aliases: ['俄罗斯联邦', 'Russian Federation'] },
  '乌克兰': { code: 'UA', name: 'Ukraine', aliases: ['乌克兰'] },
  '白俄罗斯': { code: 'BY', name: 'Belarus', aliases: ['白俄罗斯共和国'] },
  '波兰': { code: 'PL', name: 'Poland', aliases: ['波兰共和国'] },
  '印度': { code: 'IN', name: 'India', aliases: ['印度共和国', 'Republic of India'] },
  '巴基斯坦': { code: 'PK', name: 'Pakistan', aliases: ['巴基斯坦伊斯兰共和国'] },
  '孟加拉国': { code: 'BD', name: 'Bangladesh', aliases: ['孟加拉人民共和国'] },
  '斯里兰卡': { code: 'LK', name: 'Sri Lanka', aliases: ['斯里兰卡民主社会主义共和国'] },
  '尼泊尔': { code: 'NP', name: 'Nepal', aliases: ['尼泊尔联邦民主共和国'] },
  '不丹': { code: 'BT', name: 'Bhutan', aliases: ['不丹王国'] },
  '缅甸': { code: 'MM', name: 'Myanmar', aliases: ['缅甸联邦共和国', 'Burma'] },
  '泰国': { code: 'TH', name: 'Thailand', aliases: ['泰王国'] },
  '越南': { code: 'VN', name: 'Vietnam', aliases: ['越南社会主义共和国'] },
  '柬埔寨': { code: 'KH', name: 'Cambodia', aliases: ['柬埔寨王国'] },
  '老挝': { code: 'LA', name: 'Laos', aliases: ['老挝人民民主共和国'] },
  '马来西亚': { code: 'MY', name: 'Malaysia', aliases: ['马来西亚'] },
  '新加坡': { code: 'SG', name: 'Singapore', aliases: ['新加坡共和国'] },
  '印度尼西亚': { code: 'ID', name: 'Indonesia', aliases: ['印度尼西亚共和国'] },
  '菲律宾': { code: 'PH', name: 'Philippines', aliases: ['菲律宾共和国'] },
  '文莱': { code: 'BN', name: 'Brunei', aliases: ['文莱达鲁萨兰国'] },
  '东帝汶': { code: 'TL', name: 'Timor-Leste', aliases: ['东帝汶民主共和国'] },
  '澳大利亚': { code: 'AU', name: 'Australia', aliases: ['澳大利亚联邦'] },
  '新西兰': { code: 'NZ', name: 'New Zealand', aliases: ['新西兰'] },
  '加拿大': { code: 'CA', name: 'Canada', aliases: ['加拿大'] },
  '墨西哥': { code: 'MX', name: 'Mexico', aliases: ['墨西哥合众国'] },
  '巴西': { code: 'BR', name: 'Brazil', aliases: ['巴西联邦共和国'] },
  '阿根廷': { code: 'AR', name: 'Argentina', aliases: ['阿根廷共和国'] },
  '智利': { code: 'CL', name: 'Chile', aliases: ['智利共和国'] },
  '秘鲁': { code: 'PE', name: 'Peru', aliases: ['秘鲁共和国'] },
  '哥伦比亚': { code: 'CO', name: 'Colombia', aliases: ['哥伦比亚共和国'] },
  '委内瑞拉': { code: 'VE', name: 'Venezuela', aliases: ['委内瑞拉玻利瓦尔共和国'] },
  '厄瓜多尔': { code: 'EC', name: 'Ecuador', aliases: ['厄瓜多尔共和国'] },
  '玻利维亚': { code: 'BO', name: 'Bolivia', aliases: ['多民族玻利维亚国'] },
  '巴拉圭': { code: 'PY', name: 'Paraguay', aliases: ['巴拉圭共和国'] },
  '乌拉圭': { code: 'UY', name: 'Uruguay', aliases: ['乌拉圭东岸共和国'] },
  '古巴': { code: 'CU', name: 'Cuba', aliases: ['古巴共和国'] },
  '巴拿马': { code: 'PA', name: 'Panama', aliases: ['巴拿马共和国'] },
  '哥斯达黎加': { code: 'CR', name: 'Costa Rica', aliases: ['哥斯达黎加共和国'] },
  '洪都拉斯': { code: 'HN', name: 'Honduras', aliases: ['洪都拉斯共和国'] },
  '危地马拉': { code: 'GT', name: 'Guatemala', aliases: ['危地马拉共和国'] },
  '萨尔瓦多': { code: 'SV', name: 'El Salvador', aliases: ['萨尔瓦多共和国'] },
  '尼加拉瓜': { code: 'NI', name: 'Nicaragua', aliases: ['尼加拉瓜共和国'] },
  '多米尼加': { code: 'DO', name: 'Dominican Republic', aliases: ['多米尼加共和国'] },
  '牙买加': { code: 'JM', name: 'Jamaica', aliases: ['牙买加'] },
  '巴哈马': { code: 'BS', name: 'Bahamas', aliases: ['巴哈马国'] },
  '埃及': { code: 'EG', name: 'Egypt', aliases: ['阿拉伯埃及共和国'] },
  '南非': { code: 'ZA', name: 'South Africa', aliases: ['南非共和国'] },
  '尼日利亚': { code: 'NG', name: 'Nigeria', aliases: ['尼日利亚联邦共和国'] },
  '肯尼亚': { code: 'KE', name: 'Kenya', aliases: ['肯尼亚共和国'] },
  '坦桑尼亚': { code: 'TZ', name: 'Tanzania', aliases: ['坦桑尼亚联合共和国'] },
  '乌干达': { code: 'UG', name: 'Uganda', aliases: ['乌干达共和国'] },
  '埃塞俄比亚': { code: 'ET', name: 'Ethiopia', aliases: ['埃塞俄比亚联邦民主共和国'] },
  '摩洛哥': { code: 'MA', name: 'Morocco', aliases: ['摩洛哥王国'] },
  '阿尔及利亚': { code: 'DZ', name: 'Algeria', aliases: ['阿尔及利亚民主人民共和国'] },
  '突尼斯': { code: 'TN', name: 'Tunisia', aliases: ['突尼斯共和国'] },
  '利比亚': { code: 'LY', name: 'Libya', aliases: ['利比亚国'] },
  '苏丹': { code: 'SD', name: 'Sudan', aliases: ['苏丹共和国'] },
  '南苏丹': { code: 'SS', name: 'South Sudan', aliases: ['南苏丹共和国'] },
  '刚果(金)': { code: 'CD', name: 'Democratic Republic of the Congo', aliases: ['刚果民主共和国'] },
  '刚果(布)': { code: 'CG', name: 'Republic of the Congo', aliases: ['刚果共和国'] },
  '安哥拉': { code: 'AO', name: 'Angola', aliases: ['安哥拉共和国'] },
  '莫桑比克': { code: 'MZ', name: 'Mozambique', aliases: ['莫桑比克共和国'] },
  '马达加斯加': { code: 'MG', name: 'Madagascar', aliases: ['马达加斯加共和国'] },
  '津巴布韦': { code: 'ZW', name: 'Zimbabwe', aliases: ['津巴布韦共和国'] },
  '赞比亚': { code: 'ZM', name: 'Zambia', aliases: ['赞比亚共和国'] },
  '博茨瓦纳': { code: 'BW', name: 'Botswana', aliases: ['博茨瓦纳共和国'] },
  '纳米比亚': { code: 'NA', name: 'Namibia', aliases: ['纳米比亚共和国'] },
  '毛里求斯': { code: 'MU', name: 'Mauritius', aliases: ['毛里求斯共和国'] },
  '塞舌尔': { code: 'SC', name: 'Seychelles', aliases: ['塞舌尔共和国'] },
  '沙特阿拉伯': { code: 'SA', name: 'Saudi Arabia', aliases: ['沙特阿拉伯王国'] },
  '阿联酋': { code: 'AE', name: 'United Arab Emirates', aliases: ['阿拉伯联合酋长国'] },
  '卡塔尔': { code: 'QA', name: 'Qatar', aliases: ['卡塔尔国'] },
  '科威特': { code: 'KW', name: 'Kuwait', aliases: ['科威特国'] },
  '巴林': { code: 'BH', name: 'Bahrain', aliases: ['巴林王国'] },
  '阿曼': { code: 'OM', name: 'Oman', aliases: ['阿曼苏丹国'] },
  '也门': { code: 'YE', name: 'Yemen', aliases: ['也门共和国'] },
  '伊拉克': { code: 'IQ', name: 'Iraq', aliases: ['伊拉克共和国'] },
  '伊朗': { code: 'IR', name: 'Iran', aliases: ['伊朗伊斯兰共和国'] },
  '叙利亚': { code: 'SY', name: 'Syria', aliases: ['阿拉伯叙利亚共和国'] },
  '黎巴嫩': { code: 'LB', name: 'Lebanon', aliases: ['黎巴嫩共和国'] },
  '约旦': { code: 'JO', name: 'Jordan', aliases: ['约旦哈希姆王国'] },
  '以色列': { code: 'IL', name: 'Israel', aliases: ['以色列国'] },
  '巴勒斯坦': { code: 'PS', name: 'Palestine', aliases: ['巴勒斯坦国'] },
  '格鲁吉亚': { code: 'GE', name: 'Georgia', aliases: ['格鲁吉亚'] },
  '亚美尼亚': { code: 'AM', name: 'Armenia', aliases: ['亚美尼亚共和国'] },
  '阿塞拜疆': { code: 'AZ', name: 'Azerbaijan', aliases: ['阿塞拜疆共和国'] },
  '哈萨克斯坦': { code: 'KZ', name: 'Kazakhstan', aliases: ['哈萨克斯坦共和国'] },
  '乌兹别克斯坦': { code: 'UZ', name: 'Uzbekistan', aliases: ['乌兹别克斯坦共和国'] },
  '吉尔吉斯斯坦': { code: 'KG', name: 'Kyrgyzstan', aliases: ['吉尔吉斯共和国'] },
  '塔吉克斯坦': { code: 'TJ', name: 'Tajikistan', aliases: ['塔吉克斯坦共和国'] },
  '土库曼斯坦': { code: 'TM', name: 'Turkmenistan', aliases: ['土库曼斯坦'] },
  '蒙古': { code: 'MN', name: 'Mongolia', aliases: ['蒙古国'] },
  '朝鲜': { code: 'KP', name: 'North Korea', aliases: ['朝鲜民主主义人民共和国'] },
  '阿富汗': { code: 'AF', name: 'Afghanistan', aliases: ['阿富汗伊斯兰共和国'] },
  '马尔代夫': { code: 'MV', name: 'Maldives', aliases: ['马尔代夫共和国'] },
  '也门': { code: 'YE', name: 'Yemen', aliases: ['也门共和国'] },
  // 英文名称映射
  'China': { code: 'CN', name: 'China', aliases: ['CN', 'PRC'] },
  'United States': { code: 'US', name: 'United States', aliases: ['USA', 'U.S.', 'U.S.A.'] },
  'Japan': { code: 'JP', name: 'Japan', aliases: ['JPN', 'Nippon'] },
  'South Korea': { code: 'KR', name: 'South Korea', aliases: ['Korea', 'ROK'] },
  'United Kingdom': { code: 'GB', name: 'United Kingdom', aliases: ['UK', 'Great Britain'] },
  'France': { code: 'FR', name: 'France', aliases: ['French'] },
  'Germany': { code: 'DE', name: 'Germany', aliases: ['Deutschland', 'GER'] },
  'Italy': { code: 'IT', name: 'Italy', aliases: ['Italian'] },
  'Spain': { code: 'ES', name: 'Spain', aliases: ['Spanish'] },
  'Portugal': { code: 'PT', name: 'Portugal', aliases: ['Portuguese'] },
  'Netherlands': { code: 'NL', name: 'Netherlands', aliases: ['Dutch', 'Holland'] },
  'Belgium': { code: 'BE', name: 'Belgium', aliases: ['Belgian'] },
  'Switzerland': { code: 'CH', name: 'Switzerland', aliases: ['Swiss'] },
  'Austria': { code: 'AT', name: 'Austria', aliases: ['Austrian'] },
  'Sweden': { code: 'SE', name: 'Sweden', aliases: ['Swedish'] },
  'Norway': { code: 'NO', name: 'Norway', aliases: ['Norwegian'] },
  'Denmark': { code: 'DK', name: 'Denmark', aliases: ['Danish'] },
  'Finland': { code: 'FI', name: 'Finland', aliases: ['Finnish'] },
  'Iceland': { code: 'IS', name: 'Iceland', aliases: ['Icelandic'] },
  'Ireland': { code: 'IE', name: 'Ireland', aliases: ['Irish'] },
  'Poland': { code: 'PL', name: 'Poland', aliases: ['Polish'] },
  'Czech Republic': { code: 'CZ', name: 'Czech Republic', aliases: ['Czech'] },
  'Hungary': { code: 'HU', name: 'Hungary', aliases: ['Hungarian'] },
  'Slovakia': { code: 'SK', name: 'Slovakia', aliases: ['Slovak'] },
  'Slovenia': { code: 'SI', name: 'Slovenia', aliases: ['Slovenian'] },
  'Croatia': { code: 'HR', name: 'Croatia', aliases: ['Croatian'] },
  'Serbia': { code: 'RS', name: 'Serbia', aliases: ['Serbian'] },
  'Bulgaria': { code: 'BG', name: 'Bulgaria', aliases: ['Bulgarian'] },
  'Romania': { code: 'RO', name: 'Romania', aliases: ['Romanian'] },
  'Greece': { code: 'GR', name: 'Greece', aliases: ['Greek', 'Hellenic'] },
  'Turkey': { code: 'TR', name: 'Turkey', aliases: ['Turkish'] },
  'Russia': { code: 'RU', name: 'Russia', aliases: ['Russian', 'USSR'] },
  'Ukraine': { code: 'UA', name: 'Ukraine', aliases: ['Ukrainian'] },
  'Belarus': { code: 'BY', name: 'Belarus', aliases: ['Belarusian'] },
  'India': { code: 'IN', name: 'India', aliases: ['Indian'] },
  'Pakistan': { code: 'PK', name: 'Pakistan', aliases: ['Pakistani'] },
  'Bangladesh': { code: 'BD', name: 'Bangladesh', aliases: ['Bangladeshi'] },
  'Sri Lanka': { code: 'LK', name: 'Sri Lanka', aliases: ['Sri Lankan'] },
  'Nepal': { code: 'NP', name: 'Nepal', aliases: ['Nepalese'] },
  'Bhutan': { code: 'BT', name: 'Bhutan', aliases: ['Bhutanese'] },
  'Myanmar': { code: 'MM', name: 'Myanmar', aliases: ['Burmese'] },
  'Thailand': { code: 'TH', name: 'Thailand', aliases: ['Thai'] },
  'Vietnam': { code: 'VN', name: 'Vietnam', aliases: ['Vietnamese'] },
  'Cambodia': { code: 'KH', name: 'Cambodia', aliases: ['Cambodian'] },
  'Laos': { code: 'LA', name: 'Laos', aliases: ['Lao'] },
  'Malaysia': { code: 'MY', name: 'Malaysia', aliases: ['Malaysian'] },
  'Singapore': { code: 'SG', name: 'Singapore', aliases: ['Singaporean'] },
  'Indonesia': { code: 'ID', name: 'Indonesia', aliases: ['Indonesian'] },
  'Philippines': { code: 'PH', name: 'Philippines', aliases: ['Filipino'] },
  'Brunei': { code: 'BN', name: 'Brunei', aliases: ['Bruneian'] },
  'Australia': { code: 'AU', name: 'Australia', aliases: ['Australian'] },
  'New Zealand': { code: 'NZ', name: 'New Zealand', aliases: ['New Zealander'] },
  'Canada': { code: 'CA', name: 'Canada', aliases: ['Canadian'] },
  'Mexico': { code: 'MX', name: 'Mexico', aliases: ['Mexican'] },
  'Brazil': { code: 'BR', name: 'Brazil', aliases: ['Brazilian'] },
  'Argentina': { code: 'AR', name: 'Argentina', aliases: ['Argentine'] },
  'Chile': { code: 'CL', name: 'Chile', aliases: ['Chilean'] },
  'Peru': { code: 'PE', name: 'Peru', aliases: ['Peruvian'] },
  'Colombia': { code: 'CO', name: 'Colombia', aliases: ['Colombian'] },
  'Venezuela': { code: 'VE', name: 'Venezuela', aliases: ['Venezuelan'] },
  'Ecuador': { code: 'EC', name: 'Ecuador', aliases: ['Ecuadorian'] },
  'Bolivia': { code: 'BO', name: 'Bolivia', aliases: ['Bolivian'] },
  'Paraguay': { code: 'PY', name: 'Paraguay', aliases: ['Paraguayan'] },
  'Uruguay': { code: 'UY', name: 'Uruguay', aliases: ['Uruguayan'] },
  'Cuba': { code: 'CU', name: 'Cuba', aliases: ['Cuban'] },
  'Panama': { code: 'PA', name: 'Panama', aliases: ['Panamanian'] },
  'Costa Rica': { code: 'CR', name: 'Costa Rica', aliases: ['Costa Rican'] },
  'Egypt': { code: 'EG', name: 'Egypt', aliases: ['Egyptian'] },
  'South Africa': { code: 'ZA', name: 'South Africa', aliases: ['South African'] },
  'Nigeria': { code: 'NG', name: 'Nigeria', aliases: ['Nigerian'] },
  'Kenya': { code: 'KE', name: 'Kenya', aliases: ['Kenyan'] },
  'Tanzania': { code: 'TZ', name: 'Tanzania', aliases: ['Tanzanian'] },
  'Uganda': { code: 'UG', name: 'Uganda', aliases: ['Ugandan'] },
  'Ethiopia': { code: 'ET', name: 'Ethiopia', aliases: ['Ethiopian'] },
  'Morocco': { code: 'MA', name: 'Morocco', aliases: ['Moroccan'] },
  'Algeria': { code: 'DZ', name: 'Algeria', aliases: ['Algerian'] },
  'Tunisia': { code: 'TN', name: 'Tunisia', aliases: ['Tunisian'] },
  'Libya': { code: 'LY', name: 'Libya', aliases: ['Libyan'] },
  'Sudan': { code: 'SD', name: 'Sudan', aliases: ['Sudanese'] },
  'South Sudan': { code: 'SS', name: 'South Sudan', aliases: ['South Sudanese'] },
  'Saudi Arabia': { code: 'SA', name: 'Saudi Arabia', aliases: ['Saudi', 'KSA'] },
  'United Arab Emirates': { code: 'AE', name: 'United Arab Emirates', aliases: ['UAE', 'Emirates'] },
  'Qatar': { code: 'QA', name: 'Qatar', aliases: ['Qatari'] },
  'Kuwait': { code: 'KW', name: 'Kuwait', aliases: ['Kuwaiti'] },
  'Bahrain': { code: 'BH', name: 'Bahrain', aliases: ['Bahraini'] },
  'Oman': { code: 'OM', name: 'Oman', aliases: ['Omani'] },
  'Iraq': { code: 'IQ', name: 'Iraq', aliases: ['Iraqi'] },
  'Iran': { code: 'IR', name: 'Iran', aliases: ['Iranian'] },
  'Syria': { code: 'SY', name: 'Syria', aliases: ['Syrian'] },
  'Lebanon': { code: 'LB', name: 'Lebanon', aliases: ['Lebanese'] },
  'Jordan': { code: 'JO', name: 'Jordan', aliases: ['Jordanian'] },
  'Israel': { code: 'IL', name: 'Israel', aliases: ['Israeli'] },
  'Palestine': { code: 'PS', name: 'Palestine', aliases: ['Palestinian'] },
  'Georgia': { code: 'GE', name: 'Georgia', aliases: ['Georgian'] },
  'Armenia': { code: 'AM', name: 'Armenia', aliases: ['Armenian'] },
  'Azerbaijan': { code: 'AZ', name: 'Azerbaijan', aliases: ['Azerbaijani'] },
  'Kazakhstan': { code: 'KZ', name: 'Kazakhstan', aliases: ['Kazakh'] },
  'Uzbekistan': { code: 'UZ', name: 'Uzbekistan', aliases: ['Uzbek'] },
  'Kyrgyzstan': { code: 'KG', name: 'Kyrgyzstan', aliases: ['Kyrgyz'] },
  'Tajikistan': { code: 'TJ', name: 'Tajikistan', aliases: ['Tajik'] },
  'Turkmenistan': { code: 'TM', name: 'Turkmenistan', aliases: ['Turkmen'] },
  'Mongolia': { code: 'MN', name: 'Mongolia', aliases: ['Mongolian'] },
  'North Korea': { code: 'KP', name: 'North Korea', aliases: ['DPRK'] },
  'Afghanistan': { code: 'AF', name: 'Afghanistan', aliases: ['Afghan'] },
  'Maldives': { code: 'MV', name: 'Maldives', aliases: ['Maldivian'] },
}

// ISO 3166-1 alpha-2 代码映射
export const isoCodeMap = {
  'CN': 'China',
  'US': 'United States',
  'JP': 'Japan',
  'KR': 'South Korea',
  'GB': 'United Kingdom',
  'FR': 'France',
  'DE': 'Germany',
  'IT': 'Italy',
  'ES': 'Spain',
  'PT': 'Portugal',
  'NL': 'Netherlands',
  'BE': 'Belgium',
  'LU': 'Luxembourg',
  'CH': 'Switzerland',
  'AT': 'Austria',
  'SE': 'Sweden',
  'NO': 'Norway',
  'DK': 'Denmark',
  'FI': 'Finland',
  'IS': 'Iceland',
  'IE': 'Ireland',
  'PL': 'Poland',
  'CZ': 'Czech Republic',
  'SK': 'Slovakia',
  'HU': 'Hungary',
  'SI': 'Slovenia',
  'HR': 'Croatia',
  'RS': 'Serbia',
  'BG': 'Bulgaria',
  'RO': 'Romania',
  'GR': 'Greece',
  'TR': 'Turkey',
  'RU': 'Russia',
  'UA': 'Ukraine',
  'BY': 'Belarus',
  'IN': 'India',
  'PK': 'Pakistan',
  'BD': 'Bangladesh',
  'LK': 'Sri Lanka',
  'NP': 'Nepal',
  'BT': 'Bhutan',
  'MM': 'Myanmar',
  'TH': 'Thailand',
  'VN': 'Vietnam',
  'KH': 'Cambodia',
  'LA': 'Laos',
  'MY': 'Malaysia',
  'SG': 'Singapore',
  'ID': 'Indonesia',
  'PH': 'Philippines',
  'BN': 'Brunei',
  'TL': 'Timor-Leste',
  'AU': 'Australia',
  'NZ': 'New Zealand',
  'CA': 'Canada',
  'MX': 'Mexico',
  'BR': 'Brazil',
  'AR': 'Argentina',
  'CL': 'Chile',
  'PE': 'Peru',
  'CO': 'Colombia',
  'VE': 'Venezuela',
  'EC': 'Ecuador',
  'BO': 'Bolivia',
  'PY': 'Paraguay',
  'UY': 'Uruguay',
  'CU': 'Cuba',
  'PA': 'Panama',
  'CR': 'Costa Rica',
  'HN': 'Honduras',
  'GT': 'Guatemala',
  'SV': 'El Salvador',
  'NI': 'Nicaragua',
  'DO': 'Dominican Republic',
  'JM': 'Jamaica',
  'BS': 'Bahamas',
  'EG': 'Egypt',
  'ZA': 'South Africa',
  'NG': 'Nigeria',
  'KE': 'Kenya',
  'TZ': 'Tanzania',
  'UG': 'Uganda',
  'ET': 'Ethiopia',
  'MA': 'Morocco',
  'DZ': 'Algeria',
  'TN': 'Tunisia',
  'LY': 'Libya',
  'SD': 'Sudan',
  'SS': 'South Sudan',
  'CD': 'Democratic Republic of the Congo',
  'CG': 'Republic of the Congo',
  'AO': 'Angola',
  'MZ': 'Mozambique',
  'MG': 'Madagascar',
  'ZW': 'Zimbabwe',
  'ZM': 'Zambia',
  'BW': 'Botswana',
  'NA': 'Namibia',
  'MU': 'Mauritius',
  'SC': 'Seychelles',
  'SA': 'Saudi Arabia',
  'AE': 'United Arab Emirates',
  'QA': 'Qatar',
  'KW': 'Kuwait',
  'BH': 'Bahrain',
  'OM': 'Oman',
  'YE': 'Yemen',
  'IQ': 'Iraq',
  'IR': 'Iran',
  'SY': 'Syria',
  'LB': 'Lebanon',
  'JO': 'Jordan',
  'IL': 'Israel',
  'PS': 'Palestine',
  'GE': 'Georgia',
  'AM': 'Armenia',
  'AZ': 'Azerbaijan',
  'KZ': 'Kazakhstan',
  'UZ': 'Uzbekistan',
  'KG': 'Kyrgyzstan',
  'TJ': 'Tajikistan',
  'TM': 'Turkmenistan',
  'MN': 'Mongolia',
  'KP': 'North Korea',
  'AF': 'Afghanistan',
  'MV': 'Maldives',
}

// 城市名称与国家映射
export const cityCountryMap = {
  '北京': 'CN',
  '上海': 'CN',
  '广州': 'CN',
  '深圳': 'CN',
  '香港': 'CN',
  '澳门': 'CN',
  '台北': 'CN',
  '东京': 'JP',
  '大阪': 'JP',
  '京都': 'JP',
  '首尔': 'KR',
  '釜山': 'KR',
  '仁川': 'KR',
  '纽约': 'US',
  '洛杉矶': 'US',
  '芝加哥': 'US',
  '休斯顿': 'US',
  '迈阿密': 'US',
  '旧金山': 'US',
  '华盛顿': 'US',
  '伦敦': 'GB',
  '曼彻斯特': 'GB',
  '伯明翰': 'GB',
  '爱丁堡': 'GB',
  '巴黎': 'FR',
  '里昂': 'FR',
  '马赛': 'FR',
  '柏林': 'DE',
  '慕尼黑': 'DE',
  '汉堡': 'DE',
  '法兰克福': 'DE',
  '罗马': 'IT',
  '米兰': 'IT',
  '威尼斯': 'IT',
  '马德里': 'ES',
  '巴塞罗那': 'ES',
  '阿姆斯特丹': 'NL',
  '鹿特丹': 'NL',
  '布鲁塞尔': 'BE',
  '安特卫普': 'BE',
  '苏黎世': 'CH',
  '日内瓦': 'CH',
  '维也纳': 'AT',
  '斯德哥尔摩': 'SE',
  '哥本哈根': 'DK',
  '奥斯陆': 'NO',
  '赫尔辛基': 'FI',
  '雷克雅未克': 'IS',
  '都柏林': 'IE',
  '华沙': 'PL',
  '布拉格': 'CZ',
  '布达佩斯': 'HU',
  '萨格勒布': 'HR',
  '贝尔格莱德': 'RS',
  '索菲亚': 'BG',
  '布加勒斯特': 'RO',
  '雅典': 'GR',
  '伊斯坦布尔': 'TR',
  '安卡拉': 'TR',
  '莫斯科': 'RU',
  '圣彼得堡': 'RU',
  '基辅': 'UA',
  '明斯克': 'BY',
  '新德里': 'IN',
  '孟买': 'IN',
  '加尔各答': 'IN',
  '班加罗尔': 'IN',
  '卡拉奇': 'PK',
  '拉合尔': 'PK',
  '达卡': 'BD',
  '科伦坡': 'LK',
  '加德满都': 'NP',
  '仰光': 'MM',
  '曼谷': 'TH',
  '清迈': 'TH',
  '胡志明市': 'VN',
  '河内': 'VN',
  '金边': 'KH',
  '万象': 'LA',
  '吉隆坡': 'MY',
  '槟城': 'MY',
  '新加坡': 'SG',
  '雅加达': 'ID',
  '泗水': 'ID',
  '马尼拉': 'PH',
  '宿务': 'PH',
  '斯里巴加湾市': 'BN',
  '悉尼': 'AU',
  '墨尔本': 'AU',
  '布里斯班': 'AU',
  '奥克兰': 'NZ',
  '惠灵顿': 'NZ',
  '多伦多': 'CA',
  '温哥华': 'CA',
  '蒙特利尔': 'CA',
  '渥太华': 'CA',
  '墨西哥城': 'MX',
  '瓜达拉哈拉': 'MX',
  '圣保罗': 'BR',
  '里约热内卢': 'BR',
  '布宜诺斯艾利斯': 'AR',
  '圣地亚哥': 'CL',
  '利马': 'PE',
  '波哥大': 'CO',
  '加拉加斯': 'VE',
  '基多': 'EC',
  '拉巴斯': 'BO',
  '亚松森': 'PY',
  '蒙得维的亚': 'UY',
  '哈瓦那': 'CU',
  '巴拿马城': 'PA',
  '圣何塞': 'CR',
  '开罗': 'EG',
  '亚历山大': 'EG',
  '约翰内斯堡': 'ZA',
  '开普敦': 'ZA',
  '拉各斯': 'NG',
  '内罗毕': 'KE',
  '达累斯萨拉姆': 'TZ',
  '坎帕拉': 'UG',
  '亚的斯亚贝巴': 'ET',
  '拉巴特': 'MA',
  '阿尔及尔': 'DZ',
  '突尼斯': 'TN',
  '的黎波里': 'LY',
  '喀土穆': 'SD',
  '朱巴': 'SS',
  '金沙萨': 'CD',
  '布拉柴维尔': 'CG',
  '罗安达': 'AO',
  '马普托': 'MZ',
  '塔那那利佛': 'MG',
  '哈拉雷': 'ZW',
  '卢萨卡': 'ZM',
  '哈博罗内': 'BW',
  '温得和克': 'NA',
  '路易港': 'MU',
  '维多利亚': 'SC',
  '利雅得': 'SA',
  '吉达': 'SA',
  '阿布扎比': 'AE',
  '迪拜': 'AE',
  '多哈': 'QA',
  '科威特城': 'KW',
  '麦纳麦': 'BH',
  '马斯喀特': 'OM',
  '萨那': 'YE',
  '巴格达': 'IQ',
  '德黑兰': 'IR',
  '大马士革': 'SY',
  '贝鲁特': 'LB',
  '安曼': 'JO',
  '特拉维夫': 'IL',
  '耶路撒冷': 'IL',
  '加沙': 'PS',
  '第比利斯': 'GE',
  '埃里温': 'AM',
  '巴库': 'AZ',
  '努尔苏丹': 'KZ',
  '塔什干': 'UZ',
  '比什凯克': 'KG',
  '杜尚别': 'TJ',
  '阿什哈巴德': 'TM',
  '乌兰巴托': 'MN',
  '平壤': 'KP',
  '喀布尔': 'AF',
  '马累': 'MV',
}

// 地址模式匹配
export const addressPatterns = {
  postalCode: {
    'US': /\b\d{5}(-\d{4})?\b/,
    'CA': /\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b/i,
    'GB': /\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b/i,
    'DE': /\b\d{5}\b/,
    'FR': /\b\d{5}\b/,
    'JP': /\b\d{3}-\d{4}\b/,
    'CN': /\b\d{6}\b/,
    'KR': /\b\d{5}\b/,
    'AU': /\b\d{4}\b/,
    'NZ': /\b\d{4}\b/,
    'BR': /\b\d{5}-\d{3}\b/,
    'RU': /\b\d{6}\b/,
    'IN': /\b\d{6}\b/,
    'SG': /\b\d{6}\b/,
    'HK': /\b\d{6}\b/,
  },
  state: {
    'US': /\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b/i,
    'CA': /\b(AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\b/i,
    'AU': /\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b/i,
  },
}

/**
 * 地址解析函数
 * @param {string} address - 地址字符串
 * @returns {Object} - 解析结果，包含国家代码等信息
 */
export function parseAddress(address) {
  if (!address || typeof address !== 'string') {
    return { countryCode: null, countryName: null, confidence: 0 }
  }

  const cleanAddress = address.trim().toLowerCase()
  let countryCode = null
  let countryName = null
  let confidence = 0

  // 1. 检查城市名称
  for (const [city, code] of Object.entries(cityCountryMap)) {
    if (cleanAddress.includes(city.toLowerCase())) {
      countryCode = code
      countryName = isoCodeMap[code]
      confidence = 0.95
      break
    }
  }

  // 2. 检查国家名称和别名
  if (!countryCode) {
    for (const [name, data] of Object.entries(countryDatabase)) {
      if (cleanAddress.includes(name.toLowerCase())) {
        countryCode = data.code
        countryName = data.name
        confidence = 0.9
        break
      }
      // 检查别名
      for (const alias of data.aliases) {
        if (cleanAddress.includes(alias.toLowerCase())) {
          countryCode = data.code
          countryName = data.name
          confidence = 0.85
          break
        }
      }
      if (countryCode) break
    }
  }

  // 3. 检查ISO代码
  if (!countryCode) {
    const isoMatch = cleanAddress.match(/\b([A-Za-z]{2})\b/)
    if (isoMatch && isoCodeMap[isoMatch[1].toUpperCase()]) {
      countryCode = isoMatch[1].toUpperCase()
      countryName = isoCodeMap[countryCode]
      confidence = 0.8
    }
  }

  // 4. 检查邮政编码模式
  if (!countryCode) {
    for (const [code, pattern] of Object.entries(addressPatterns.postalCode)) {
      if (pattern.test(address)) {
        countryCode = code
        countryName = isoCodeMap[code]
        confidence = 0.7
        break
      }
    }
  }

  // 5. 检查州代码
  if (!countryCode) {
    for (const [code, pattern] of Object.entries(addressPatterns.state)) {
      if (pattern.test(address)) {
        countryCode = code
        countryName = isoCodeMap[code]
        confidence = 0.75
        break
      }
    }
  }

  // 6. 处理模糊地址 - 基于常见地址格式特征
  if (!countryCode) {
    const features = {
      hasChinese: /[\u4e00-\u9fa5]/.test(address),
      hasJapanese: /[\u3040-\u30ff\u31f0-\u31ff]/.test(address),
      hasKorean: /[\uac00-\ud7af]/.test(address),
      hasArabic: /[\u0600-\u06ff]/.test(address),
      hasRussian: /[\u0400-\u04ff]/.test(address),
    }

    if (features.hasChinese) {
      countryCode = 'CN'
      countryName = 'China'
      confidence = 0.6
    } else if (features.hasJapanese) {
      countryCode = 'JP'
      countryName = 'Japan'
      confidence = 0.6
    } else if (features.hasKorean) {
      countryCode = 'KR'
      countryName = 'South Korea'
      confidence = 0.6
    } else if (features.hasArabic) {
      countryCode = 'AE'
      countryName = 'United Arab Emirates'
      confidence = 0.4
    } else if (features.hasRussian) {
      countryCode = 'RU'
      countryName = 'Russia'
      confidence = 0.6
    }
  }

  return {
    countryCode,
    countryName,
    confidence,
    originalAddress: address
  }
}

/**
 * 批量解析地址
 * @param {Array} addresses - 地址数组
 * @returns {Array} - 解析结果数组
 */
export function parseAddresses(addresses) {
  if (!Array.isArray(addresses)) {
    return []
  }

  return addresses.map(address => parseAddress(address))
}

/**
 * 获取国家信息
 * @param {string} identifier - 国家名称、ISO代码或别名
 * @returns {Object|null} - 国家信息
 */
export function getCountryInfo(identifier) {
  if (!identifier) return null

  const upperIdentifier = identifier.toUpperCase().trim()
  const lowerIdentifier = identifier.toLowerCase().trim()

  // 首先检查ISO代码
  if (upperIdentifier.length === 2 && isoCodeMap[upperIdentifier]) {
    return {
      code: upperIdentifier,
      name: isoCodeMap[upperIdentifier],
      aliases: countryDatabase[isoCodeMap[upperIdentifier]]?.aliases || []
    }
  }

  // 检查国家名称
  for (const [name, data] of Object.entries(countryDatabase)) {
    if (name.toLowerCase() === lowerIdentifier) {
      return {
        code: data.code,
        name: data.name,
        aliases: data.aliases
      }
    }
    // 检查别名
    if (data.aliases.some(alias => alias.toLowerCase() === lowerIdentifier)) {
      return {
        code: data.code,
        name: data.name,
        aliases: data.aliases
      }
    }
  }

  return null
}

/**
 * 模糊匹配国家
 * @param {string} input - 输入字符串
 * @param {number} threshold - 相似度阈值 (0-1)
 * @returns {Array} - 匹配结果数组
 */
export function fuzzyMatchCountry(input, threshold = 0.6) {
  if (!input) return []

  const lowerInput = input.toLowerCase().trim()
  const results = []

  for (const [name, data] of Object.entries(countryDatabase)) {
    // 计算相似度
    const similarity = calculateSimilarity(lowerInput, name.toLowerCase())
    
    if (similarity >= threshold) {
      results.push({
        code: data.code,
        name: data.name,
        matchName: name,
        similarity
      })
    }

    // 检查别名
    for (const alias of data.aliases) {
      const aliasSimilarity = calculateSimilarity(lowerInput, alias.toLowerCase())
      if (aliasSimilarity >= threshold) {
        results.push({
          code: data.code,
          name: data.name,
          matchName: alias,
          similarity: aliasSimilarity
        })
      }
    }
  }

  // 按相似度排序
  results.sort((a, b) => b.similarity - a.similarity)

  return results
}

/**
 * 计算字符串相似度 (Levenshtein距离)
 * @param {string} s1 - 字符串1
 * @param {string} s2 - 字符串2
 * @returns {number} - 相似度 (0-1)
 */
function calculateSimilarity(s1, s2) {
  if (s1 === s2) return 1
  if (s1.length === 0 || s2.length === 0) return 0

  const matrix = Array(s2.length + 1).fill(null).map(() => Array(s1.length + 1).fill(0))

  for (let i = 0; i <= s1.length; i++) matrix[0][i] = i
  for (let j = 0; j <= s2.length; j++) matrix[j][0] = j

  for (let j = 1; j <= s2.length; j++) {
    for (let i = 1; i <= s1.length; i++) {
      const cost = s1[i - 1] === s2[j - 1] ? 0 : 1
      matrix[j][i] = Math.min(
        matrix[j - 1][i] + 1,
        matrix[j][i - 1] + 1,
        matrix[j - 1][i - 1] + cost
      )
    }
  }

  const distance = matrix[s2.length][s1.length]
  const maxLength = Math.max(s1.length, s2.length)

  return 1 - (distance / maxLength)
}