-- Migration 0011: events/confidence 入库（geo_events 表 + entity_geometries.confidence 列）
-- 使数据库成为事件与置信度的权威来源。回填出埃及42站 + 保罗36城。
-- 幂等：geo_events 为空时才回填。Depends on 0007/0008/0010。

ALTER TABLE entity_geometries ADD COLUMN IF NOT EXISTS confidence VARCHAR(16);

CREATE TABLE IF NOT EXISTS geo_events (
    event_id      SERIAL PRIMARY KEY,
    entity_id     INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    seq           INT NOT NULL DEFAULT 0,
    title         TEXT NOT NULL,
    scripture_ref VARCHAR(32),
    summary       TEXT
);
CREATE INDEX IF NOT EXISTS idx_geo_events_entity ON geo_events (entity_id, seq);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM geo_events) THEN
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='兰塞');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '逾越节之后出发', '出12:37', '以色列人吃完逾越节羊羔，从兰塞起行往疏割去，约有步行的男人六十万。' FROM entity_names WHERE name_zh='兰塞';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='疏割');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '耶和华昼夜引导', '出13:21', '白天云柱、夜间火柱在前头行，照亮道路。' FROM entity_names WHERE name_zh='疏割';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以倘');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '安营在旷野边缘', '出13:20', '在旷野边的以倘安营。' FROM entity_names WHERE name_zh='以倘';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='比哈希录（过红海）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '过红海，法老追兵覆没', '出14:21-28', '摩西伸杖，海水分开，以色列人走干地过海；法老的车辆马兵随后下海，水回流将其淹没。' FROM entity_names WHERE name_zh='比哈希录（过红海）';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '米利暗的凯歌', '出15:20-21', '女先知米利暗手拿鼓，众妇女随她歌舞，颂赞耶和华大大战胜。' FROM entity_names WHERE name_zh='比哈希录（过红海）';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='玛拉');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '苦水变甜', '出15:23-25', '百姓因水苦发怨言，耶和华指示摩西把一棵树丢进水里，水就变甜。' FROM entity_names WHERE name_zh='玛拉';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以琳');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '十二股水泉、七十棵棕树', '出15:27', '到了以琳，那里有十二股水泉、七十棵棕树，就在水边安营。' FROM entity_names WHERE name_zh='以琳';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='红海边');
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='汛的旷野');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '天降吗哪与鹌鹑', '出16:13-15', '晚上有鹌鹑遮满营地，早晨降下吗哪如白霜，作为四十年的日用饮食。' FROM entity_names WHERE name_zh='汛的旷野';
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='脱加');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚录');
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='利非订');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '击打磐石出水', '出17:5-6', '百姓无水喝，耶和华吩咐摩西击打何烈的磐石，就有水流出供百姓饮用。' FROM entity_names WHERE name_zh='利非订';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '与亚玛力人争战', '出17:11-13', '摩西举手以色列得胜；亚伦与户珥扶他的手到日落，约书亚击败亚玛力人。' FROM entity_names WHERE name_zh='利非订';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='西奈山');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '颁布十诫与立约', '出20:1-17', '耶和华在烟火雷电中降临西奈山，亲口宣告十条诫命，与以色列立约。' FROM entity_names WHERE name_zh='西奈山';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '金牛犊与会幕', '出32; 出40', '百姓铸金牛犊犯罪；其后照耶和华的样式建造会幕，荣耀充满帐幕。' FROM entity_names WHERE name_zh='西奈山';
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='基博罗哈他瓦（贪欲之坟）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '贪欲与鹌鹑之灾', '民11:31-34', '百姓贪恋肉食，耶和华降下大量鹌鹑，随后以重灾击杀贪欲的人，故名"贪欲的坟墓"。' FROM entity_names WHERE name_zh='基博罗哈他瓦（贪欲之坟）';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='哈洗录');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '米利暗与亚伦毁谤摩西', '民12:1-10', '米利暗与亚伦因摩西的妻子毁谤他，米利暗长了大麻风，经摩西代求后得医治。' FROM entity_names WHERE name_zh='哈洗录';
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='利提玛');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='临门帕烈');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='立拿');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='勒撒');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='基希拉他');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='沙斐山');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='哈拉大');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='玛吉希录');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='他哈');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='他拉');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='密加');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='哈摩拿');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='摩西录');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='比尼亚干');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='曷哈及甲');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='约巴他');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='阿博拿');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以旬迦别');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '红海北端的港口', '王上9:26', '后世所罗门在此（亚喀巴湾畔）建造船队的港口；以色列人曾在此安营。' FROM entity_names WHERE name_zh='以旬迦别';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='加低斯（寻的旷野）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '十二个探子窥探迦南', '民13:25-14:4', '探子回报后百姓发怨言不肯进迦南，被罚在旷野漂流四十年，直到那世代倒毙。' FROM entity_names WHERE name_zh='加低斯（寻的旷野）';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '米利暗逝世', '民20:1', '以色列全会众到了寻的旷野加低斯，米利暗死在那里，葬在那里。' FROM entity_names WHERE name_zh='加低斯（寻的旷野）';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 2, '摩西击磐石犯罪', '民20:10-12', '摩西没有照吩咐"吩咐"磐石，反而两次击打它，因不尊耶和华为圣，被禁止进入应许之地。' FROM entity_names WHERE name_zh='加低斯（寻的旷野）';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='何珥山');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '亚伦逝世', '民20:25-28', '亚伦在何珥山顶脱下圣衣给以利亚撒，死在山上，全会众为他哀哭三十天。' FROM entity_names WHERE name_zh='何珥山';
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='撒摩拿（铜蛇事件）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '铜蛇与火蛇', '民21:6-9', '百姓发怨言，耶和华使火蛇咬死多人；摩西照命造铜蛇挂木杆上，仰望铜蛇的就得存活。' FROM entity_names WHERE name_zh='撒摩拿（铜蛇事件）';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='普嫩');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='阿伯');
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以耶亚巴琳');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='底本迦得');
    UPDATE entity_geometries SET confidence='unknown' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚门低比拉太音');
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚巴琳山（尼波前）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '摩西遥望应许之地', '申34:1-4', '摩西上尼波山的毗斯迦山顶，耶和华把全地指给他看：这就是我向亚伯拉罕、以撒、雅各起誓应许之地。' FROM entity_names WHERE name_zh='亚巴琳山（尼波前）';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='摩押平原（什亭）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '巴兰的预言', '民23-24', '摩押王巴勒雇巴兰咒诅以色列，巴兰却被神感动连连祝福，预言"有星要出于雅各"。' FROM entity_names WHERE name_zh='摩押平原（什亭）';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '摩西临终讲论与逝世', '申命记; 申34:5', '摩西在此向新一代宣讲申命记的训诲，随后在尼波山逝世，约书亚接续带领进入迦南。' FROM entity_names WHERE name_zh='摩押平原（什亭）';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='安提阿（叙利亚）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '宣教事工的母会', '徒13:1-3', '安提阿教会禁食祷告，圣灵差派巴拿巴和扫罗（保罗）出去传道，三次旅程皆由此出发。' FROM entity_names WHERE name_zh='安提阿（叙利亚）';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='西流基');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='撒拉米');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '在居比路（塞浦路斯）传道', '徒13:5', '到了撒拉米，就在犹太人的会堂里传讲神的道。' FROM entity_names WHERE name_zh='撒拉米';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='帕弗');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '行法术的以吕马受罚', '徒13:6-12', '保罗斥责术士以吕马，他即刻瞎眼；方伯士求·保罗见此希奇，就信了主。' FROM entity_names WHERE name_zh='帕弗';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='别加');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '约翰马可离队', '徒13:13', '到了旁非利亚的别加，约翰马可离开他们回耶路撒冷去了。' FROM entity_names WHERE name_zh='别加';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚大利');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='彼西底的安提阿');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '会堂讲道，转向外邦', '徒13:16-48', '保罗在会堂讲述救恩历史；犹太人嫉妒抵挡，保罗宣告转向外邦人，外邦人欢喜领受。' FROM entity_names WHERE name_zh='彼西底的安提阿';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以哥念');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '险被石头打', '徒14:1-6', '许多人信主，但城里分党，有人要凌辱用石头打他们，二人就逃往路司得、特庇。' FROM entity_names WHERE name_zh='以哥念';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='路司得');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '医好生来瘸腿的人', '徒14:8-18', '保罗医好瘸腿者，众人以为是神（宙斯、希耳米）下凡，要献祭，二人极力拦阻。' FROM entity_names WHERE name_zh='路司得';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '保罗被石头打', '徒14:19-20', '有犹太人挑唆众人用石头打保罗，以为他死了拖到城外；门徒围着他，他起来又进城。' FROM entity_names WHERE name_zh='路司得';
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='特庇');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='特罗亚');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '马其顿的异象', '徒16:9-10', '夜间保罗见异象：一个马其顿人求他过去帮助；福音由此首次踏入欧洲。' FROM entity_names WHERE name_zh='特罗亚';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '犹推古从窗台坠落复生', '徒20:7-12', '保罗讲道到半夜，少年犹推古困倦从三楼坠下，保罗下去抱住他，他活了。' FROM entity_names WHERE name_zh='特罗亚';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='撒摩特喇');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='尼亚波利');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='腓立比');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '吕底亚归主', '徒16:13-15', '卖紫色布的妇人吕底亚听道，主开她的心，她和全家受洗，欧洲首位信徒。' FROM entity_names WHERE name_zh='腓立比';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '下监与狱卒全家信主', '徒16:25-34', '保罗西拉在狱中唱诗祷告，地大震动监门全开；狱卒要自尽被拦，问当怎样行才可得救，当夜全家受洗。' FROM entity_names WHERE name_zh='腓立比';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='暗妃波里');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚波罗尼亚');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='帖撒罗尼迦');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '三个安息日辩道', '徒17:1-9', '保罗一连三个安息日在会堂讲论；信的人不少，不信的犹太人聚众生乱。' FROM entity_names WHERE name_zh='帖撒罗尼迦';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='庇哩亚');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '甘心领受、天天考查圣经', '徒17:10-12', '庇哩亚人比帖撒罗尼迦人开明，甘心领受这道，天天考查圣经，要晓得是否如此。' FROM entity_names WHERE name_zh='庇哩亚';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='雅典');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '亚略巴古讲"未识之神"', '徒17:22-31', '保罗站在亚略巴古，借坛上"未识之神"传讲创造主与复活的福音。' FROM entity_names WHERE name_zh='雅典';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='哥林多');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '住一年半，与百基拉亚居拉同工', '徒18:1-11', '保罗与织帐棚的亚居拉、百基拉同住做工，在此住了一年六个月教导神的道。' FROM entity_names WHERE name_zh='哥林多';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='坚革哩');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='以弗所');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '两年之久，主道兴旺', '徒19:8-10', '保罗在推喇奴学房天天辩论，达两年，全亚细亚的人都听见主的道。' FROM entity_names WHERE name_zh='以弗所';
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 1, '银匠为亚底米起哄乱', '徒19:23-41', '银匠底米丢因偶像生意受损，煽动全城高喊"大哉以弗所人的亚底米"，满城混乱。' FROM entity_names WHERE name_zh='以弗所';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='米利都');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '向以弗所长老告别', '徒20:17-38', '保罗召以弗所长老来米利都，托付他们牧养神的教会，众人痛哭与他送别。' FROM entity_names WHERE name_zh='米利都';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='推罗');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='凯撒利亚');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '押往罗马的起点', '徒27:1', '保罗与别的囚犯交给百夫长犹流，从这里上船往意大利去。' FROM entity_names WHERE name_zh='凯撒利亚';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='耶路撒冷');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '旅程的终点与被捕', '徒21:17-33', '保罗回到耶路撒冷，在圣殿被犹太人围攻，被罗马千夫长拘押，开启赴罗马受审之路。' FROM entity_names WHERE name_zh='耶路撒冷';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='西顿');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='每拉');
    UPDATE entity_geometries SET confidence='approximate' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='佳澳（革哩底）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '保罗预警航行危险', '徒27:9-12', '保罗劝阻继续航行，但百夫长信从船主，多数人主张开船离开佳澳。' FROM entity_names WHERE name_zh='佳澳（革哩底）';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='米利大（马耳他）');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '海难得救、毒蛇无害', '徒28:1-6', '船破众人游泳上岸到米利大岛；毒蛇咬保罗的手而他毫无所害，土人以为他是神。' FROM entity_names WHERE name_zh='米利大（马耳他）';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='叙拉古');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='利基翁');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='部丢利');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='罗马');
    INSERT INTO geo_events(entity_id, seq, title, scripture_ref, summary) SELECT entity_id, 0, '在罗马放胆传道', '徒28:30-31', '保罗在自己所租的房子住了两年，放胆传讲神国的道，将主耶稣基督的事教导人，并没有人禁止。' FROM entity_names WHERE name_zh='罗马';
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='亚朔');
    UPDATE entity_geometries SET confidence='identified' WHERE entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh='米推利尼');
  END IF;
END $$;
