# -*- coding: utf-8 -*-
"""2026-11-24 日次10本の総評を600字超に追記する（batch_20261124_daily.py のあとに実行）。冪等。"""
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent.parent / "content" / "tiers"
MARK = "【ひとこと】"
EXTRA = {
    "food-aona-ryori": "【ひとこと】冬の青菜は、安くて、早くて、体にもうれしい味方。迷ったら、まず「おひたし」と「味噌汁」から。慣れてきたら、バターや卵と合わせて、洋風にも広げてみてほしい。あなたの青菜のS級は、どの食べ方だった？ ぜひ並べ替えて、自分のTier表を作ってみよう。",
    "kurashi-fuyu-kasanegi": "【ひとこと】重ね着は、寒さとの戦いではなく、「調整する楽しみ」。朝は着込んで、昼は1枚脱ぐ。夜はまた羽織る。そのくらいの気楽さで、毎日を快適に過ごしてほしい。あなたの冬の定番アイテムは、どれ？ ぜひ自分のランクも作ってみよう。",
    "money-souryou-herasu": "【ひとこと】節約は、がまんではなく「仕組み」。リストを作る、まとめて買う、1日おく。この3つを習慣にすれば、送料も無駄買いも自然に減っていく。まずは次の注文から、カートに入れたまま1日おいてみよう。意外なほど、冷静に選べるはず。",
    "travel-yosan-tatekata": "【ひとこと】予算を決めるのは、楽しみを減らすためではなく、安心して楽しむため。メリハリをつけて、「ここぞ」という場所には思い切って使おう。旅の後に「あの1食は、かけて正解だった」と思えたら、それが良い予算の使い方。あなたの旅のS級は、何にお金をかけたい？",
    "manabi-sumaho-yuuwaku": "【ひとこと】スマホをがまんできないのは、意志が弱いからではない。そもそも、そう作られている。だから、「見えない・届かない・鳴らない」の環境づくりで、味方につけよう。まずは今日30分だけ、別の部屋に置いてみる。それだけで、勉強の進み方が変わるかもしれない。",
    "music-chuuko-gakki": "【ひとこと】中古楽器は、うまく選べば、新品より良い出会いがあることも。ポイントは、焦らず、比べて、確認すること。お店の人にたくさん質問して、納得してから決めよう。最初の1台が、長い付き合いの相棒になるかもしれない。音を出す日が、楽しみだね。",
    "sns-follow-seiri": "【ひとこと】フォロー整理は、「大掃除」ではなく「模様替え」くらいの気持ちでいい。年末に少しだけ見直して、新年を気持ちよく迎えよう。整理したあとは、好きなアカウントを新しく見つけるのも楽しい。自分にとって、居心地のいいタイムラインを育てていこう。",
    "shumi-pan-zukuri-hajime": "【ひとこと】最初から完璧なパンを目指さなくて大丈夫。ちょっと固くても、形がいびつでも、焼きたてはおいしい。3回、4回と焼くうちに、生地の感触が分かってくる。寒い休日に、部屋をあたたかくしながら、気楽に1個目を焼いてみてほしい。あなたの1個目は、何パンにする？",
    "neko-cat-tower-erabi": "【ひとこと】キャットタワーは、飼い主にとっても、猫にとっても長い付き合いになる家具。見た目より、まずは安全と安定感。猫がお気に入りの場所にしてくれたら、それだけで、毎日の暮らしがもっと楽しくなる。あなたの猫は、高いところ派？ 低いところ派？ ぜひ教えてほしい。",
    "yattemitai-toshikoshi-yoru": "【ひとこと】特別なことをしなくても、「今年もがんばったね」と自分に声をかける夜で、十分。やることは3つだけ。温かい飲み物を片手に、ゆっくり1年を締めくくろう。来年の自分に、一言メッセージを残しておくのも、おすすめ。素敵な年越しになりますように。",
}
for slug, add in EXTRA.items():
    p = OUT / f"{slug}.yaml"
    y = yaml.safe_load(p.read_text(encoding="utf-8"))
    if MARK in y["summary"]:
        continue
    y["summary"] = y["summary"].rstrip() + "\n" + add
    p.write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=100000, default_flow_style=False), encoding="utf-8")
    print(slug, len(y["summary"]))

MARK2 = "【補足】"
EXTRA2 = {
    "money-souryou-herasu": "【補足】送料の条件は店ごとに違い、途中で変わることもある。注文の前に、そのつど確認する習慣をつけておくと安心。",
    "travel-yosan-tatekata": "【補足】料金や割引の条件は時期で変わるので、予約の前に公式サイトで最新の情報を見ておくと安心。",
    "manabi-sumaho-yuuwaku": "【補足】集中が切れたら、無理に続けず、立ち上がって水を飲む、軽く伸びをするなど、スマホ以外の休憩を挟もう。",
    "music-chuuko-gakki": "【補足】楽器の種類で見るポイントは違う。弦楽器は反りや弦高、鍵盤は鍵の戻りや音の出方など、分からなければ店員さんに聞こう。",
    "sns-follow-seiri": "【補足】整理の基準は人それぞれ。「見て心が軽くなるか」を一つの目安にして、迷ったらミュートで様子を見るのがおすすめ。",
    "shumi-pan-zukuri-hajime": "【補足】オーブンは機種で温度のくせが違う。焼き色を見ながら、時間を数分ずつ調整して、自分の家の最適を見つけよう。",
    "neko-cat-tower-erabi": "【補足】猫の様子で選ぶのが一番。高いところが好きか、隠れるのが好きか、普段の行動をよく観察してから決めよう。",
}
for slug, add in EXTRA2.items():
    p = OUT / f"{slug}.yaml"
    y = yaml.safe_load(p.read_text(encoding="utf-8"))
    if MARK2 in y["summary"]:
        continue
    y["summary"] = y["summary"].rstrip() + "\n" + add
    p.write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False, width=100000, default_flow_style=False), encoding="utf-8")
    print(slug, len(y["summary"]))
