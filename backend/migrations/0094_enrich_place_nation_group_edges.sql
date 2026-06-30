-- 0094_enrich_place_nation_group_edges.sql
-- 丰富关系图谱：为「地点 / 邦国 / 群体」节点补全与人物的关系边，使其不再孤立、可展开。
-- 复用 0068 的解析模式：character 按姓名解析为图谱节点；非人物按 kind||'-'||slug 直接定位节点。
-- 名称匹配不到的行会被安全跳过；ON CONFLICT DO NOTHING 保证幂等可重复执行。
-- 字段：source_kind|source_ref|target_kind|target_slug|relationship_type|category|label_zh|scripture|description|weight
WITH raw(line) AS (SELECT * FROM regexp_split_to_table($edges$
character|亚伯拉罕|place|hebron|LIVED_IN|location|居于幔利|创13:18|亚伯拉罕在希伯仑幔利的橡树旁居住筑坛。|2.0
character|大卫|place|hebron|REIGNED_IN|location|先在希伯仑作王|撒下2:1-4|大卫先在希伯仑作犹大王七年半。|2.0
character|押沙龙|place|hebron|REBELLED_AT|location|举旗叛乱|撒下15:10|押沙龙在希伯仑起兵叛父。|1.5
character|路得|place|bethlehem|SETTLED_IN|location|归回伯利恒|得1:22|路得随拿俄米回到伯利恒。|1.8
character|波阿斯|place|bethlehem|LIVED_IN|location|本城财主|得2:1|波阿斯是伯利恒有财力的亲属。|1.6
character|大卫|place|bethlehem|BORN_IN|location|大卫的家乡|撒上16:1|大卫是伯利恒耶西之子。|2.0
character|撒母耳|place|bethlehem|ANOINTED_AT|location|膏立大卫|撒上16:13|撒母耳在伯利恒膏大卫为王。|1.6
character|耶稣|place|bethlehem|BORN_IN|location|降生之地|路2:4-7|基督照预言生在伯利恒。|2.2
character|约瑟|place|egypt|RULED_IN|location|作埃及宰相|创41:41|约瑟被法老立为埃及宰相。|2.0
character|雅各|place|egypt|MIGRATED_TO|location|全家下埃及|创46:6|雅各因饥荒举家迁往埃及。|1.8
character|摩西|place|egypt|DELIVERED_FROM|location|领民出埃及|出12:51|摩西领以色列人出埃及。|2.2
character|约书亚|place|jericho|CONQUERED|location|攻陷耶利哥|书6:20|约书亚绕城七日城墙倒塌。|2.0
character|喇合|place|jericho|LIVED_IN|location|接待探子|书2:1|喇合住耶利哥城墙上隐藏探子。|1.6
character|撒该|place|jericho|LIVED_IN|location|税吏长悔改|路19:1-10|耶稣在耶利哥呼召税吏长撒该。|1.5
character|亚伯拉罕|place|canaan|MIGRATED_TO|location|进应许之地|创12:5|亚伯拉罕奉召进入迦南。|1.8
character|约书亚|place|canaan|CONQUERED|location|分地为业|书11:23|约书亚得地分给各支派。|1.8
character|迦勒|place|canaan|INHERITED_IN|location|得希伯仑为业|书14:13|迦勒八十五岁仍求山地为业。|1.5
character|保罗|place|damascus|CONVERTED_NEAR|location|路上蒙光照|徒9:3-6|扫罗往大马士革途中遇主。|2.0
character|亚拿尼亚|place|damascus|LIVED_IN|location|为扫罗按手|徒9:10-17|大马士革的门徒亚拿尼亚使扫罗复明。|1.4
character|巴拿巴|place|antioch|MINISTERED_IN|location|牧养安提阿|徒11:22-26|巴拿巴在安提阿教导门徒一年。|1.8
character|保罗|place|antioch|SENT_FROM|location|差传起点|徒13:1-3|保罗从安提阿被差往外邦宣教。|1.8
character|保罗|place|corinth|MINISTERED_IN|location|住一年半|徒18:11|保罗在哥林多传道建立教会。|1.8
character|亚居拉|place|corinth|LIVED_IN|location|同业织帐棚|徒18:2-3|亚居拉与保罗同住同工。|1.4
character|百基拉|place|corinth|LIVED_IN|location|保罗同工|徒18:2|百基拉与丈夫接待造就保罗。|1.4
character|保罗|place|ephesus|MINISTERED_IN|location|住约三年|徒19:8-10|保罗在以弗所天天辩论传道。|1.8
character|提摩太|place|ephesus|MINISTERED_IN|location|牧养教会|提前1:3|提摩太奉派留在以弗所牧会。|1.5
character|约翰|place|ephesus|MINISTERED_IN|location|晚年牧养|约壹1|使徒约翰晚年在以弗所事奉(传统)。|1.2
character|耶稣|place|galilee|MINISTERED_IN|location|加利利传道|太4:23|耶稣走遍加利利宣讲天国。|2.0
character|彼得|place|galilee|CALLED_AT|location|蒙召作门徒|太4:18-20|彼得在加利利海边蒙召。|1.6
character|耶稣|place|golgotha|CRUCIFIED_AT|location|被钉十架|约19:17-18|耶稣在各各他受难。|2.2
character|拉撒路|place|bethany|RAISED_IN|location|死里复活|约11:1-44|拉撒路在伯大尼被主叫醒。|1.6
character|马大|place|bethany|LIVED_IN|location|接待主|路10:38|马大在伯大尼家中服事。|1.4
character|马利亚|place|bethany|ANOINTED_AT|location|膏主预备安葬|约12:1-3|马利亚在伯大尼用香膏抹主。|1.4
character|大卫|place|en-gedi|HID_AT|location|躲避扫罗|撒上24:1|大卫在隐基底旷野割扫罗衣襟。|1.5
character|扫罗|place|endor|VISITED|location|求问交鬼妇人|撒上28:7|扫罗夜访隐多珥交鬼妇人。|1.4
character|扫罗|place|gibeah|FROM|location|扫罗的本城|撒上10:26|基比亚是扫罗的家乡。|1.4
character|以撒|place|gerar|SOJOURNED_IN|location|寄居挖井|创26:1-6|以撒因饥荒寄居基拉耳。|1.4
character|亚伯拉罕|place|gerar|SOJOURNED_IN|location|寄居|创20:1|亚伯拉罕寄居基拉耳。|1.3
character|但以理|place|babylon|EXILED_TO|location|被掳服事|但1:1-6|但以理被掳至巴比伦事奉。|1.8
character|以西结|place|babylon|EXILED_TO|location|迦巴鲁河边|结1:1|以西结在巴比伦被掳得异象。|1.6
character|巴拿巴|place|cyprus|FROM|location|居比路人|徒4:36|巴拿巴是居比路出生的利未人。|1.4
character|保罗|place|cyprus|MINISTERED_IN|location|首次旅行|徒13:4-12|保罗在居比路传道。|1.4
character|约拿|place|nineveh|PREACHED_IN|location|宣讲悔改|拿3:3-4|约拿在尼尼微宣告审判,全城悔改。|1.8
character|那鸿|place|nineveh|PROPHESIED_AGAINST|location|预言倾覆|鸿1:1|那鸿预言尼尼微的审判。|1.3
character|耶稣|place|nazareth|GREW_UP_IN|location|长大之地|路2:39-40|耶稣在拿撒勒长大。|1.8
character|马利亚|place|nazareth|LIVED_IN|location|天使报信|路1:26-31|天使在拿撒勒向马利亚报信。|1.5
character|摩西|place|mount-sinai|RECEIVED_LAW_AT|location|领受十诫|出19-20|摩西在西奈山领受律法。|2.0
character|以利亚|place|mount-sinai|FLED_TO|location|何烈山遇神|王上19:8|以利亚逃到神的山遇见微声。|1.5
character|约书亚|place|jordan|CROSSED|location|过约旦河|书3:14-17|约书亚领民踏干地过约旦河。|1.6
character|施洗约翰|place|jordan|BAPTIZED_IN|location|约旦河施洗|太3:6|施洗约翰在约旦河为人施洗。|1.8
character|耶稣|place|jordan|BAPTIZED_IN|location|受洗|太3:13-17|耶稣在约旦河受洗。|1.8
character|乃缦|place|jordan|HEALED_IN|location|沐浴得洁|王下5:14|乃缦在约旦河沐浴七次大麻风得洁净。|1.4
character|以利沙|place|jordan|PARTED|location|分开河水|王下2:14|以利沙用以利亚外衣分开约旦河。|1.3
character|暗利|place|samaria|FOUNDED|location|建撒玛利亚|王上16:24|暗利买山建造撒玛利亚为都。|1.4
character|亚哈|place|samaria|REIGNED_IN|location|北国都城|王上16:29|亚哈在撒玛利亚作以色列王。|1.5
character|腓利|place|samaria|EVANGELIZED_IN|location|传福音|徒8:5|腓利下撒玛利亚宣讲基督。|1.4
character|雅各|place|shechem|SETTLED_IN|location|筑坛|创33:18-20|雅各到示剑支搭帐棚筑坛。|1.4
character|约书亚|place|shechem|RENEWED_COVENANT_AT|location|重立圣约|书24:1-25|约书亚在示剑与民立约。|1.5
character|大卫|place|ziklag|LIVED_IN|location|非利士赐城|撒上27:6|亚吉将洗革拉赐给大卫居住。|1.4
character|大卫|place|mahanaim|FLED_TO|location|避押沙龙|撒下17:24|大卫逃到玛哈念。|1.3
character|雅各|place|mahanaim|NAMED|location|神的军兵|创32:1-2|雅各见神的使者称那地玛哈念。|1.2
character|亚哈|place|jezreel|REIGNED_IN|location|王宫与拿伯园|王上21:1|亚哈在耶斯列夺拿伯葡萄园。|1.4
character|耶洗别|place|jezreel|DIED_AT|location|坠楼而死|王下9:30-37|耶洗别在耶斯列被掷下楼。|1.4
character|保罗|place|malta|SHIPWRECKED_AT|location|海难获救|徒28:1-6|保罗船破漂到马耳他岛。|1.4
character|保罗|place|philippi|MINISTERED_IN|location|建立教会|徒16:12-15|保罗在腓立比领吕底亚信主。|1.6
character|吕底亚|place|philippi|CONVERTED_IN|location|卖紫布的|徒16:14|吕底亚在腓立比开心领受福音。|1.4
character|保罗|place|rome|IMPRISONED_IN|location|被囚传道|徒28:16-31|保罗在罗马被软禁仍传神国。|1.6
character|以斯帖|place|susa|LIVED_IN|location|书珊王后|斯2:8-17|以斯帖在书珊宫中立为王后。|1.8
character|末底改|place|susa|LIVED_IN|location|坐朝门|斯2:21|末底改在书珊朝门当差。|1.5
character|尼希米|place|susa|SERVED_IN|location|作王的酒政|尼1:1-11|尼希米在书珊宫作王酒政。|1.5
character|但以理|place|susa|SAW_VISION_IN|location|得异象|但8:2|但以理在书珊城得异象。|1.3
character|古列|place|persia|REIGNED_IN|location|下诏归回|拉1:1-4|波斯王古列准犹大人归回。|1.5
character|以斯拉|place|persia|SENT_FROM|location|奉命归回|拉7:6-10|以斯拉从波斯带律法书归回。|1.4
character|参孙|place|timnah|MARRIED_IN|location|娶非利士女|士14:1-2|参孙在亭拿娶非利士女子。|1.3
character|保罗|place|colossae|WROTE_TO|location|致歌罗西书|西1:2|保罗写信给歌罗西教会。|1.3
character|押沙龙|place|geshur|FLED_TO|location|外祖之地|撒下13:37-38|押沙龙逃往外祖父基述王那里。|1.3
character|路得|nation|moab|FROM|political|摩押女子|得1:4|路得是归信耶和华的摩押女子。|1.8
character|巴勒|nation|moab|KING_OF|political|摩押王|民22:4|巴勒雇巴兰咒诅以色列。|1.4
character|巴兰|nation|moab|SUMMONED_TO|spiritual|受召咒诅|民22:5-6|巴兰被召却祝福以色列。|1.4
character|摩西|nation|midian|FLED_TO|political|逃亡牧羊|出2:15|摩西逃到米甸牧羊四十年。|1.8
character|叶忒罗|nation|midian|PRIEST_OF|spiritual|米甸祭司|出3:1|叶忒罗是米甸祭司、摩西岳父。|1.5
character|基甸|nation|midian|DEFEATED|political|战胜米甸|士7:19-25|基甸以三百人破米甸大军。|1.6
character|歌利亚|nation|philistia|FROM|political|迦特巨人|撒上17:4|歌利亚是非利士迦特的巨人。|1.6
character|参孙|nation|philistia|FOUGHT|political|对抗非利士|士15:14-15|参孙击杀非利士人。|1.5
character|大卫|nation|philistia|DEFEATED|political|击败非利士|撒下5:17-25|大卫屡次战胜非利士人。|1.5
character|扫罗|nation|amalek|FOUGHT|political|未灭尽亚玛力|撒上15:9|扫罗因留亚甲牲畜被弃。|1.5
character|撒母耳|nation|amalek|JUDGED|spiritual|处死亚甲|撒上15:33|撒母耳在吉甲杀亚玛力王亚甲。|1.4
character|约书亚|nation|amalek|DEFEATED|political|利非订之战|出17:13|约书亚在利非订杀败亚玛力。|1.4
character|西拿基立|nation|assyria-empire|KING_OF|political|亚述王围城|王下18:13|西拿基立上来攻击犹大坚城。|1.5
character|希西家|nation|assyria-empire|RESISTED|spiritual|祷告蒙拯救|王下19:14-19|希西家祷告,耶和华击杀亚述军。|1.6
character|约拿|nation|assyria-empire|SENT_TO|spiritual|往尼尼微|拿1:2|约拿奉差往亚述京城尼尼微。|1.4
character|尼布甲尼撒|nation|babylon-empire|KING_OF|political|巴比伦王|但2:1|尼布甲尼撒掳掠犹大、立金像。|1.8
character|但以理|nation|babylon-empire|SERVED_IN|spiritual|被掳贤臣|但1:19-20|但以理在巴比伦朝中有智慧。|1.6
character|伯沙撒|nation|babylon-empire|KING_OF|political|墙上写字|但5:1-6|伯沙撒筵席见墙上指头写字。|1.4
character|古列|nation|persian-empire|KING_OF|political|下诏归回|代下36:22-23|古列准被掳之民归回建殿。|1.6
character|大流士|nation|persian-empire|KING_OF|political|准重建圣殿|拉6:1-12|大流士降旨支持重建圣殿。|1.4
character|亚哈随鲁|nation|persian-empire|KING_OF|political|以斯帖之王|斯1:1-3|亚哈随鲁统治127省。|1.4
character|以斯帖|nation|persian-empire|QUEEN_OF|political|波斯王后|斯2:17|以斯帖立为波斯王后救本族。|1.6
character|尼希米|nation|persian-empire|SERVED|political|王的酒政|尼2:1|尼希米在波斯王前作酒政。|1.4
character|凯撒奥古斯都|nation|rome-empire|EMPEROR_OF|political|下旨报名|路2:1|奥古斯都下旨普天下报名上册。|1.4
character|本丢彼拉多|nation|rome-empire|GOVERNOR_OF|political|审判耶稣|约18:28-19:16|彼拉多是罗马犹太巡抚。|1.5
character|保罗|nation|rome-empire|CITIZEN_OF|political|罗马公民|徒22:25-28|保罗以罗马公民身分上诉该撒。|1.5
character|以扫|nation|edom|ANCESTOR_OF|family|以东人之祖|创36:1|以扫即以东,是以东人的始祖。|1.5
character|拿辖|nation|ammon|KING_OF|political|围基列雅比|撒上11:1-2|亚扪王拿辖羞辱基列雅比人。|1.3
character|便哈达|nation|aram-damascus|KING_OF|political|围撒玛利亚|王上20:1|亚兰王便哈达上来攻打以色列。|1.4
character|哈薛|nation|aram-damascus|KING_OF|political|受膏作王|王下8:13|哈薛照以利沙的话作亚兰王。|1.4
character|乃缦|nation|aram-damascus|COMMANDER_OF|political|亚兰元帅|王下5:1|乃缦是亚兰王的元帅,长大麻风。|1.4
character|耶罗波安|nation|northern-israel|FIRST_KING_OF|political|北国开国王|王上12:20|耶罗波安使以色列分裂、立金牛。|1.6
character|亚哈|nation|northern-israel|KING_OF|political|拜巴力|王上16:30-33|亚哈娶耶洗别引进巴力崇拜。|1.5
character|以利亚|nation|northern-israel|PROPHET_OF|spiritual|对抗巴力|王上18:20-40|以利亚在迦密山对抗巴力先知。|1.6
character|以利沙|nation|northern-israel|PROPHET_OF|spiritual|接续以利亚|王下2:13-15|以利沙接续以利亚作北国先知。|1.5
character|何细亚|nation|northern-israel|PROPHET_OF|spiritual|向北国发预言|何1:1|何细亚向北国传神的爱与审判。|1.3
character|罗波安|nation|southern-judah|FIRST_KING_OF|political|南国开国王|王上12:17|罗波安留下犹大支派为南国。|1.5
character|希西家|nation|southern-judah|KING_OF|political|宗教改革|王下18:3-6|希西家除偶像、专靠耶和华。|1.6
character|约西亚|nation|southern-judah|KING_OF|political|重修律法|王下22-23|约西亚得律法书、彻底改革。|1.5
character|以赛亚|nation|southern-judah|PROPHET_OF|spiritual|向犹大发预言|赛1:1|以赛亚在犹大列王年间事奉。|1.5
character|耶利米|nation|southern-judah|PROPHET_OF|spiritual|被掳前哀哭|耶1:1-3|耶利米向将亡的犹大呼吁悔改。|1.5
character|希兰|nation|tyre|KING_OF|political|供材建殿|王上5:1-10|推罗王希兰供应香柏木建殿。|1.3
character|所罗门|nation|tyre|ALLIED_WITH|political|盟约合作|王上5:12|所罗门与希兰立约通商。|1.3
character|扫罗|nation|united-kingdom|FIRST_KING_OF|political|以色列首王|撒上10:1|扫罗受膏作联合王国第一位王。|1.5
character|大卫|nation|united-kingdom|KING_OF|political|联合王国|撒下5:3-5|大卫统一以色列十二支派。|1.6
character|所罗门|nation|united-kingdom|KING_OF|political|国势鼎盛|王上4:20-21|所罗门治下国家强盛太平。|1.5
character|彼得|group|twelve-apostles|MEMBER_OF|spiritual|使徒之首|太10:2|彼得列十二使徒之首。|1.8
character|安得烈|group|twelve-apostles|MEMBER_OF|spiritual|彼得之弟|太10:2|安得烈引彼得见主。|1.4
character|约翰|group|twelve-apostles|MEMBER_OF|spiritual|蒙爱门徒|太10:2|约翰是主所爱的门徒。|1.6
character|腓力|group|twelve-apostles|MEMBER_OF|spiritual|使徒|太10:3|腓力引拿但业归主。|1.2
character|多马|group|twelve-apostles|MEMBER_OF|spiritual|多疑后信|约20:24-28|多马摸主肋旁认主为神。|1.3
character|马太|group|twelve-apostles|MEMBER_OF|spiritual|税吏蒙召|太9:9|马太撇下税关跟随主。|1.3
character|彼得|group|early-church|LED|spiritual|五旬节讲道|徒2:14|彼得在五旬节带领初代教会。|1.6
character|司提反|group|early-church|MARTYR_OF|spiritual|首位殉道|徒7:54-60|司提反为主殉道。|1.5
character|巴拿巴|group|early-church|MEMBER_OF|spiritual|劝慰子|徒4:36-37|巴拿巴变卖田产供教会。|1.4
character|保罗|group|early-church|MEMBER_OF|spiritual|外邦使徒|徒9:15|保罗成为外邦人的使徒。|1.5
character|巴拿巴|group|antioch-church|LED|spiritual|受差牧养|徒11:22|巴拿巴受差遣牧养安提阿。|1.4
character|保罗|group|antioch-church|MEMBER_OF|spiritual|同工教导|徒11:26|保罗在安提阿教导门徒。|1.4
character|提摩太|group|paul-coworkers|MEMBER_OF|spiritual|属灵儿子|腓2:22|提摩太与保罗如父子同心。|1.5
character|提多|group|paul-coworkers|MEMBER_OF|spiritual|真儿子|多1:4|提多是保罗同信主真儿子。|1.3
character|路加|group|paul-coworkers|MEMBER_OF|spiritual|亲爱医生|西4:14|路加是保罗的同伴、医生。|1.3
character|西拉|group|paul-coworkers|MEMBER_OF|spiritual|同行宣教|徒15:40|西拉与保罗同行第二次旅行。|1.3
character|百基拉|group|paul-coworkers|MEMBER_OF|spiritual|同工夫妇|罗16:3|百基拉与亚居拉是保罗同工。|1.3
character|亚居拉|group|paul-coworkers|MEMBER_OF|spiritual|同工夫妇|罗16:3|亚居拉与妻同工造就教会。|1.3
character|亚伦|group|levites|MEMBER_OF|spiritual|首任大祭司|出28:1|亚伦及子孙承接祭司职分。|1.6
character|摩西|group|levites|FROM|spiritual|利未支派|出2:1|摩西出自利未家。|1.4
character|可拉|group|levites|MEMBER_OF|spiritual|背叛遭罚|民16:1-33|利未人可拉党类背叛被吞灭。|1.3
character|亚伦|group|priesthood|HEAD_OF|spiritual|首任大祭司|利8:12|亚伦受膏立为大祭司。|1.6
character|以利|group|priesthood|PRIEST_OF|spiritual|示罗祭司|撒上1:9|以利在示罗作祭司士师。|1.4
character|撒督|group|priesthood|PRIEST_OF|spiritual|忠心祭司|撒下8:17|撒督在大卫朝忠心供职。|1.3
character|该亚法|group|priesthood|HIGH_PRIEST_OF|spiritual|审判耶稣|太26:57|大祭司该亚法定耶稣的罪。|1.4
character|摩西|group|israelites|LED|other|领出埃及|出14:21-31|摩西领以色列人过红海。|1.6
character|约书亚|group|israelites|LED|other|领进迦南|书1:2-6|约书亚领以色列人进应许地。|1.5
character|所罗巴伯|group|jews-returnees|LED|other|首批归回|拉3:8|所罗巴伯带领第一批被掳之民归回。|1.5
character|以斯拉|group|jews-returnees|LED|other|带律法归回|拉7:6|以斯拉带律法书与第二批归回。|1.5
character|尼希米|group|jews-returnees|LED|other|重建城墙|尼2:11-18|尼希米带领重建耶路撒冷城墙。|1.5
character|但以理|group|judah-exiles|MEMBER_OF|other|被掳贤臣|但1:6|但以理是被掳犹大的少年。|1.4
character|以西结|group|judah-exiles|MEMBER_OF|other|被掳先知|结1:1-3|以西结在被掳之民中作先知。|1.4
character|希律大帝|group|herodian-dynasty|HEAD_OF|political|杀伯利恒婴孩|太2:16|希律大帝为除新生王杀婴孩。|1.5
character|希律安提帕|group|herodian-dynasty|MEMBER_OF|political|杀施洗约翰|可6:14-29|希律安提帕斩施洗约翰。|1.4
$edges$, E'\n')), edge_seed AS (
  SELECT row_number() OVER () ord, p[1] source_kind, p[2] source_ref, p[3] target_kind, p[4] target_ref,
         p[5] relationship_type, p[6] relationship_category, p[7] label_zh, p[8] scripture_ref, p[9] description, p[10]::numeric weight
  FROM raw CROSS JOIN LATERAL (SELECT string_to_array(line,'|') p) x
  WHERE line <> '' AND line NOT LIKE '--%'),
 resolved AS (
  SELECT edge_seed.*,
         CASE WHEN source_kind='character' THEN sn.id ELSE source_kind||'-'||source_ref END source_node_id,
         CASE WHEN target_kind='character' THEN tn.id ELSE target_kind||'-'||target_ref END target_node_id
  FROM edge_seed
  LEFT JOIN biblical_characters sc ON source_kind='character' AND sc.name=source_ref AND sc.is_active=true
  LEFT JOIN biblical_graph_nodes sn ON sn.character_id=sc.id AND sn.is_active=true
  LEFT JOIN biblical_characters tc ON target_kind='character' AND tc.name=target_ref AND tc.is_active=true
  LEFT JOIN biblical_graph_nodes tn ON tn.character_id=tc.id AND tn.is_active=true)
INSERT INTO biblical_graph_edges
  (source_node_id, target_node_id, relationship_type, relationship_category, label_zh, label_en,
   scripture_ref, description, weight, confidence, is_directed, sort_order, scripture_refs, confidence_level)
SELECT source_node_id, target_node_id, relationship_type, relationship_category, label_zh, relationship_type,
       scripture_ref, description, weight, 0.85, true, 94000+ord, ARRAY_REMOVE(ARRAY[scripture_ref],NULL), 'medium'
FROM resolved
WHERE source_node_id IS NOT NULL AND target_node_id IS NOT NULL AND source_node_id <> target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=source_node_id AND n.is_active=true)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id=target_node_id AND n.is_active=true)
ON CONFLICT DO NOTHING;

-- End of 0094.
