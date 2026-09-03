---
name: amz-risk-entry
description: >
  评估 Amazon US 商品的法规与平台准入风险，包括产品安全、FDA、FCC、EPA、运输危险品、
  类目和 FBA 限制。支持 ASIN、关键词或完整产品描述；ASIN 优先读取 Product Entity，
  并在执行时核对监管机构与 Amazon 官方现行信息。用于合规、认证、能否上架、类目限制、
  Hazmat 和准入风险请求；不处理专利、商标或版权风险。
metadata:
  short-description: 检查 Amazon US 法规与平台准入风险
---

# Amazon US 准入风险

这是风险筛查，不是法律意见。法规和平台规则会变化，不能只靠 Skill 内的静态知识给结论。

## 输入与 Product 数据

优先收集：产品用途、目标人群、材料、成分、功效声明、供电和无线方式、是否含电池或液体、
包装、目标类目、发货方式和目标站点。

有 ASIN 时先调用：

```bash
amz run entity.product.product_details --param asin=<ASIN>
```

从 Product 详情读取五点、描述、品牌、完整类目、图片和规格。不要调用旧 `amz-api` 脚本，
不要另建永久缓存。Product Entity 的 TTL 只覆盖商品数据；法规事实每次任务都要重新核对。

只有关键词时，结论置信度最多为低。影响法规归类的字段缺失时，最多问 3 个问题；仍不明确的项
标为 `UNKNOWN`，不能当作通过。

## 筛查流程

1. 建立特征表：儿童、食品或皮肤接触、医疗或健康声称、电子或无线、杀虫或抗菌声称、锂电池、
   液体或气雾剂、车辆安全、纺织品、承重或夹伤风险。
2. 只检查被特征触发的监管域，不复制一张“所有产品通用”的法规表。
3. 按 [references/official-sources.md](references/official-sources.md) 打开对应官方页面，记录
   URL、页面日期或访问日期、适用条件和所需材料。
4. 在可登录的 Seller Central 中检查当前账户的类目、ASIN、品牌、成色和 FBA 限制；没有账户
   状态时，不声称“已获准销售”。
5. 区分法规义务、Amazon 平台要求和本团队的保守选品政策。三者不能混写。

## 风险等级

- `RED`：官方规则明确禁售，或当前产品方案缺少上市前必须完成的关键许可、测试或文件。
- `YELLOW`：可能适用，仍需补材料、Seller Central 验证或专业人员确认。
- `GREEN`：基于已核对的产品事实未发现额外准入要求。它不等于监管机构批准。

在内部保守选品评分中，需要专项认证或测试可记 0 分并停止；这只是业务门槛，不要描述成法律上的
“不能卖”。成本和周期没有官方或供应商报价时，写“待询价”，不要沿用旧 Skill 的固定金额。

## 输出

先输出中文 Markdown 报告，再附两个合法 JSON 对象：`compliance` 与 `platform`。
报告至少包含产品识别、触发特征、法规检查、平台检查、缺失证据、行动项和整体评级。

每个检查项必须给出：`status`、`why`、`required_action`、`source_url`、`checked_at`。
JSON 中保留 `score`、`stop`、`score_reason`、`risk_level`、`blocking_items` 和 `unknown_items`，
便于下游解析。没有登录 Seller Central 时，平台结果必须标记 `account_specific_check=false`。

出现以下情况时必须升级给合规专业人员：儿童产品、医疗器械或药品边界、食品与补充剂、杀虫或
公共健康声称、车辆安全部件、复杂电池危险品，或多个监管机构可能同时适用。
