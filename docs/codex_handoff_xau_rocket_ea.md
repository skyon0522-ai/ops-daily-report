# Codex引き継ぎ書：XAU Asymmetric Rocket EA

## 0. この文書の目的

この文書は、Codexに **GOLD / XAUUSD専用のMQL5 Expert Advisor（EA）** を設計・実装・検証させるための引き継ぎ書である。

目的は、XMTrading KIWAMI口座相当の条件を前提に、10万円程度の小資金から高い成長率を狙うEAを作ること。ただし、これは利益保証ではない。特に「10万円を1年で1億円」は通常の安全運用とは両立しないため、EAは **初期だけ攻撃的、資金が増えるほど防御的** に動くように設計する。

Codexは、相場の勝敗を保証するコードではなく、以下を満たす研究・検証用EAを作ること。

- GOLD / XAUUSD専用
- MQL5 / MT5用
- 完全自動売買に対応できる構造
- デフォルトでは安全側に倒す
- ナンピン、マーチン、損切りなしは禁止
- すべての注文にSLを必須化
- 資金フェーズごとにリスクを自動低下
- 指標、スプレッド、DD、連敗、週末で停止
- バックテスト、デモ、小額リアルを経ない本番投入を禁止

---

## 1. 重要な前提

### 1.1 目標の扱い

元の目的は「XMTradingで最大1000倍レバレッジ、資金10万円、GOLDのみ、KIWAMI口座、完全自動で1億円を目指す」である。

ただし、この目標は安全運用ではない。10万円から1億円は1000倍であり、1年で達成するには異常に高い複利成長が必要になる。したがって、Codexは以下の方針で実装する。

- 「安全に1000倍」ではなく「破産確率を管理しながら非対称な成長機会を狙う」
- 最大1000倍レバレッジは、フルレバで使うのではなく、証拠金効率として扱う
- 実際のロットは、レバレッジではなくSL幅と許容損失額から逆算する
- 小資金フェーズでは高リスクを許容する
- 資金が増えるほど強制的にリスクを下げる
- 途中出金と守備移行を仕様として組み込む

### 1.2 絶対禁止

以下の実装は禁止する。

- ナンピン
- マーチンゲール
- グリッド放置
- 損切りなし
- 指標瞬間ギャンブル
- ゼロカット前提の過大ロット
- DD中のロット増加
- 負けを取り返すためのリスク増加
- 週末持ち越し前提の設計
- スプレッド拡大中の新規注文
- SL未設定の注文
- 認証情報や口座番号のコミット

---

## 2. 最終EAコンセプト

EA仮名：`XAU_Asymmetric_Rocket_EA`

コンセプト：

> GOLDが本当に伸びる局面だけを狙い、負ける局面では即停止し、資金が増えるほど自動的に守備型へ移行するEA。

主役はトレンドフォロー。逆張りは補助。

### 2.1 対象

- 銘柄：GOLD / XAUUSD
- 口座：XMTrading KIWAMI相当を想定
- プラットフォーム：MetaTrader 5
- 言語：MQL5
- エントリー時間足：M5
- 環境認識：M15 / H1 / H4

### 2.2 戦略配分

| 戦略 | 役割 | 優先度 |
|---|---|---:|
| ロンドン・NY高安ブレイク | 本命。大波を取る | 高 |
| トレンド中の押し目・戻り売り | ブレイク後の継続を取る | 中 |
| 指標後の方向確定ブレイク | 大きな値幅を狙うが慎重に扱う | 中 |
| VWAP回帰 | レンジ時の補助。攻撃モードでは使わない | 低 |

---

## 3. リポジトリ構成

Codexは以下の構成で実装する。

```text
/MQL5/Experts/XAU_Rocket/
  XAU_Asymmetric_Rocket_EA.mq5

/MQL5/Include/XAU_Rocket/
  Config.mqh
  Types.mqh
  SymbolSpecLoader.mqh
  RiskEngine.mqh
  GuardRail.mqh
  RegimeEngine.mqh
  SignalBreakout.mqh
  SignalPullback.mqh
  SignalNewsBreakout.mqh
  SignalVWAP.mqh
  OrderManager.mqh
  PositionManager.mqh
  NewsFilter.mqh
  SessionFilter.mqh
  Logger.mqh
  Dashboard.mqh

/docs/
  codex_handoff_xau_rocket_ea.md
  mt5_compile_and_test.md
  risk_model.md
  strategy_rules.md
  validation_checklist.md
```

1ファイルにすべてを書かないこと。安全装置、リスク計算、シグナル、注文管理、ログは分離する。

---

## 4. 実装順序

Codexは以下の順番で実装する。エントリーロジックから先に作らない。

### v0.1：売買しない安全装置EA

目的：取引せず、銘柄仕様、リスク計算、停止条件、ログだけを確認する。

実装対象：

- `Config.mqh`
- `Types.mqh`
- `SymbolSpecLoader.mqh`
- `RiskEngine.mqh`
- `GuardRail.mqh`
- `Logger.mqh`
- `Dashboard.mqh`
- `XAU_Asymmetric_Rocket_EA.mq5`

必須要件：

- デフォルトで `AllowNewEntries = false`
- デフォルトで `EmergencyStop = true`
- 銘柄仕様を取得できない場合は新規停止
- tick value、tick size、contract size、min lot、lot step、stop level、spreadをログ出力
- SL幅からロットを計算
- 実効レバレッジ上限を超える場合はロット削減
- 最小ロット未満なら取引しない
- 日次損失、週次損失、最大DD、連敗、スプレッド異常で停止

v0.1では注文を出さない。

### v0.2：ブレイクアウトだけ実装

本命ロジックのみ実装する。

ロング条件：

- H1終値がEMA200より上
- H1 EMA50 > EMA200
- M15も上方向
- M5終値がDonchian20上限を明確に突破
- ADX14 >= 25
- ATR14が直近平均より上昇
- 価格がSession VWAPより上
- ロンドンまたはNY時間
- スプレッド正常
- ニュース停止中ではない
- GuardRailが許可している

ショート条件は逆。

決済：

- 初期SL：`max(ATR14 * 1.5, 直近スイング外, 最小ストップ距離 + spread補正)`
- +1Rで一部利確、残りは建値以上へ
- +2R〜3Rで一部利確
- 残りはATRトレーリング
- 一定本数伸びなければ時間切れ撤退

### v0.3：押し目・戻り売り

ロング条件：

- H1上昇
- M15上昇
- M5でEMA20 / EMA50 / VWAP付近まで押す
- RSI14が40〜55付近から反発
- 小高値を再突破
- SLは押し安値下

ショートは逆。

目的は勝率を無理に上げることではなく、ブレイク後の継続を拾うこと。取引回数が増えすぎる場合は条件を絞る。

### v0.4：指標停止と指標後ブレイク

指標瞬間エントリーは禁止。

ルール：

- 高重要度USDイベント15分前から新規停止
- 発表後3〜15分停止
- スプレッド正常化まで停止
- 初動高値・安値を形成後、その再ブレイクのみ許可
- 初動全戻しは見送り

対象イベント：

- CPI
- PPI
- PCE
- NFP
- FOMC
- FRB議長発言
- ISM
- 小売売上高
- GDP
- 雇用関連指標

MQL5経済カレンダーが利用できるなら使う。環境上使えない場合はCSV読み込み方式を用意する。カレンダー取得に失敗した場合は、fail closedとして新規停止する設定を用意する。

### v0.5：VWAP回帰

補助ロジック。攻撃モードでは禁止。

条件：

- ADX14 < 18
- ATR安定
- 価格がVWAP ±2σ以上に乖離
- RSIが極端値
- 反転足またはヒゲ確認
- TPはVWAP付近
- リスクは通常の半分以下

強トレンド時には絶対に逆張りしない。

---

## 5. リスクモデル

### 5.1 フェーズ制御

残高により自動でリスクを変える。

| フェーズ | 残高 | 1回リスク | 日次停止 | 最大DD停止 | 実効レバ上限 |
|---|---:|---:|---:|---:|---:|
| Phase 1 | 100,000〜300,000 JPY | 3.0% | -10% | -40% | 20倍 |
| Phase 2 | 300,000〜1,000,000 JPY | 2.0% | -7% | -35% | 15倍 |
| Phase 3 | 1,000,000〜5,000,000 JPY | 1.2% | -5% | -25% | 10倍 |
| Phase 4 | 5,000,000〜20,000,000 JPY | 0.8% | -3% | -18% | 6倍 |
| Phase 5 | 20,000,000〜50,000,000 JPY | 0.5% | -2% | -12% | 3倍 |
| Phase 6 | 50,000,000〜100,000,000 JPY | 0.25% | -1.5% | -10% | 2倍 |

このテーブルは入力パラメータ化する。ただし初期値は上記にする。

### 5.2 ロット計算

ロットは以下で計算する。

```text
許容損失額 = AccountEquity × PhaseRiskPercent × ModeRiskMultiplier
SL幅 = max(ATRベース, スイングベース, 最小ストップ距離 + spread補正)
ロット = 許容損失額 ÷ SL幅 ÷ 1ロットあたり価格変動価値
```

必ず以下を使ってブローカー仕様から計算する。

- `SYMBOL_TRADE_CONTRACT_SIZE`
- `SYMBOL_TRADE_TICK_SIZE`
- `SYMBOL_TRADE_TICK_VALUE`
- `SYMBOL_VOLUME_MIN`
- `SYMBOL_VOLUME_MAX`
- `SYMBOL_VOLUME_STEP`
- `SYMBOL_TRADE_STOPS_LEVEL`
- `SYMBOL_SPREAD`
- `ACCOUNT_EQUITY`
- `ACCOUNT_MARGIN_LEVEL`

必要証拠金、実効レバレッジ、最小ロット、最大ロットを必ず確認する。

---

## 6. GuardRail仕様

新規注文前に必ずGuardRailを通す。

停止条件：

- `EmergencyStop == true`
- `AllowNewEntries == false`
- 銘柄仕様取得失敗
- tick valueまたはtick sizeが異常
- スプレッドが上限超過
- 日次損失上限到達
- 週次損失上限到達
- 最大DD到達
- 3連敗でリスク半減
- 5連敗で24時間停止
- 指標停止時間
- 金曜NY午後の新規停止
- 週末持ち越し禁止時間
- 約定拒否、滑り、再接続異常が一定回数を超えた場合

判断不能な場合は取引禁止にする。

---

## 7. 攻撃モード・防御モード

### 7.1 攻撃モード

発動条件：

- H4 / H1 / M15が同方向
- ADX14 >= 30
- ATR拡大
- ロンドン高値・安値またはNY高値・安値を突破
- 当日損益がプラス
- 直近2連敗していない
- スプレッド正常
- 高重要度指標の停止時間外

攻撃モードで許可：

- フェーズ内の上限までリスク使用
- 利益方向のみピラミッディング
- +1R到達後、SLを建値以上へ移してから追加
- 追加は最大2回まで

禁止：

- 含み損中の追加
- DD中の攻撃モード
- 連敗後の攻撃モード

### 7.2 防御モード

発動条件：

- 2連敗
- 当日損失が一定以上
- レンジ判定
- ADX低下
- スプレッド拡大
- 指標前後
- 滑り悪化
- ATR異常

防御モードでは、新規停止またはリスク半減。VWAP回帰は低リスク時のみ許可する。

---

## 8. ログ仕様

CSVログを必須にする。

最低限のログ項目：

- timestamp
- symbol
- timeframe
- mode
- phase
- equity
- balance
- daily_pl
- weekly_pl
- drawdown_percent
- consecutive_losses
- spread
- atr
- adx
- ema_state
- vwap_state
- signal_name
- signal_direction
- entry_allowed
- rejection_reason
- risk_percent
- sl_distance
- calculated_lot
- final_lot
- effective_leverage
- order_ticket
- entry_price
- sl
- tp
- close_reason
- realized_pl

ログが出せない場合はEAを停止する設定を用意する。

---

## 9. ダッシュボード仕様

チャート上に以下を表示する。

```text
EA Status: RUN / STOP
EmergencyStop: true / false
AllowNewEntries: true / false
Regime: TREND / RANGE / DANGER
Mode: NORMAL / ATTACK / DEFENSE
Phase: 1-6
Risk per trade
Daily P/L
Weekly P/L
Current DD
Consecutive losses
Spread
ATR state
ADX
News filter
Session filter
Next allowed trade time
Last rejection reason
```

運用者が、なぜ止まっているかをすぐ分かるようにする。

---

## 10. バックテスト条件

MT5 Strategy Testerで以下を実施する。

| 項目 | 条件 |
|---|---|
| 期間 | 2019-01-01〜直近 |
| 銘柄 | XMのGOLD / XAUUSD実銘柄 |
| 時間足 | M5 |
| ティック | Every tick based on real ticks |
| 初期証拠金 | 100,000 JPY |
| レバレッジ | 1000:1、500:1、200:1、100:1を別々に確認 |
| スプレッド | 現在値、2倍、3倍 |
| 遅延 | No Delay、Random Delay、Fixed Delay |
| 手数料・スワップ | 口座仕様に合わせる |

最低合格基準：

- Profit Factor 1.25以上
- Recovery Factor 2.0以上
- 最大DDがフェーズ基準内
- 平均損益がプラス
- 最大連敗10回でも破綻しない
- 月次プラス率60%以上
- スプレッド2倍で破綻しない
- Random Delayで極端に崩れない
- アウトオブサンプルで崩壊しない

きれいすぎる右肩上がりは疑う。特定年だけ勝つ設定は採用しない。

---

## 11. フォワード検証

バックテスト合格後、デモで最低50トレード検証する。

確認項目：

- 指標前後に本当に止まるか
- スプレッド拡大で止まるか
- DD停止が効くか
- 連敗停止が効くか
- SL未設定注文が出ないか
- ログが欠けないか
- 実運用の滑りが許容範囲か
- バックテストとの乖離が大きすぎないか

デモで見るのは利益ではなく、EAが設計通り止まるかである。

---

## 12. 小額リアル検証

デモ合格後、1万〜3万円で小額リアル検証する。

小額リアル設定：

```text
AllowNewEntries = true
EmergencyStop = false
Risk_Per_Trade = 0.25%〜0.5%
Max_Position = 1
Pyramiding = false
Daily_Stop = 1.5%
Weekly_Stop = 4%
Max_DD_Stop = 8%
```

ここで確認するのは、利益ではなく以下。

- 実スプレッド
- 実滑り
- 約定拒否
- サーバー遅延
- VPS安定性
- ログと実履歴の一致

ここで崩れる場合、10万円本番へ進めない。

---

## 13. 出金・退避ルール

EA外の運用ルールとしてREADMEまたはdocsに明記する。

| 残高 | 行動 |
|---:|---|
| 500,000 JPY | 100,000 JPY出金して元本回収 |
| 1,000,000 JPY | 200,000 JPY出金 |
| 3,000,000 JPY | 500,000 JPY出金 |
| 10,000,000 JPY | 2,000,000 JPY以上出金 |
| 30,000,000 JPY | 5,000,000〜10,000,000 JPY出金 |
| 50,000,000 JPY | 半分を退避 |
| 100,000,000 JPY | 攻撃EA停止、守備型へ移行 |

途中で増えた資金を全額晒し続けない。

---

## 14. Codexへの具体タスク

Codexは以下を順番に実施する。

1. リポジトリ状態を確認する
2. `AGENTS.md` と既存READMEを読む
3. 上記ディレクトリ構成を作る
4. v0.1の安全装置EAを実装する
5. `docs/mt5_compile_and_test.md` を作る
6. `docs/risk_model.md` を作る
7. `docs/strategy_rules.md` を作る
8. `docs/validation_checklist.md` を作る
9. MetaEditorが使えない環境なら、その旨を明記する
10. MQL5構文上の注意点をセルフレビューする
11. 変更をコミットする
12. PR本文に未検証項目を明記する

---

## 15. 完了条件

最低限の完了条件：

- MQL5ファイル一式が作成されている
- デフォルトでは新規注文が出ない
- `EmergencyStop` が効く
- 銘柄仕様を取得してログに出せる
- ロット計算関数がある
- GuardRailが新規注文前に必ず呼ばれる
- SLなし注文が構造上出せない
- CSVログ仕様がある
- ダッシュボードがある
- docsにコンパイル・テスト手順がある
- 未実施テストが明記されている

PR本文テンプレート：

```markdown
## Summary
- ...

## Safety controls
- ...

## Testing
- [ ] MetaEditor compile: not run / passed / failed
- [ ] MT5 Strategy Tester: not run / passed / failed
- [ ] Static review: ...

## Not done
- ...

## Manual review required before demo/live use
- ...
```

---

## 16. Codexへの注意

このEAの目的は「必ず勝つこと」ではない。目的は、危険な目標を扱ううえで、裁量の暴走を減らし、損失上限と停止条件をコードに固定することである。

最も重要な仕様は、エントリー条件ではなく停止条件である。

優先順位：

1. SL必須
2. 緊急停止
3. DD停止
4. 日次・週次停止
5. スプレッド停止
6. 指標停止
7. ロット計算
8. ログ
9. ダッシュボード
10. エントリーロジック

勝つEAより先に、壊れにくいEAを作ること。
