# hreflang 审计工具

仅依赖 Python 标准库，用于解析页面与 sitemap 中的 hreflang 声明，检查双向互指、x-default 兜底和同一语言区域的主页面选择。

## 支持的声明来源

- HTML：link 标签 rel="alternate"，必须同时具备 hreflang 与 href 属性。
- Sitemap：sitemap.xml 中 url 元素内的 xhtml:link rel="alternate"。每条声明归属于同一 url 的 loc 所指页面，而不是 sitemap 文件本身。
- 页面由目录中的 .html / .htm 文件推导；index.html 表示其所在目录，例如 en/index.html 对应 /en/。
- sitemap.xml 不会被计入页面数。

## 语言标签归一

hreflang/tags.py 按 BCP 47 的常用大小写约定归一标签：

1. 去除首尾空白，把下划线和连字符统一视为子标签分隔符。
2. 主语言子标签使用小写；2 位字母地区子标签使用大写；4 位字母脚本子标签使用首字母大写。
3. 因此 zh-Hans-CN、zh-hans-cn、zh_HANS_cn 都归一为 zh-Hans-CN。
4. 地区是标签语义的一部分，zh-CN 与 zh-TW 始终是两个标签；zh-Hans 与 zh-Hans-CN 也不会合并。
5. 任意大小写或分隔符形式的 x-default 都归一为 x-default，但不会进入语言组。

## 互指校验

- 校验对象是页面之间的有向声明：若 A 的非 x-default 声明指向 B，则 B 也必须有非 x-default 声明指向 A。
- 页面指向自己的声明天然满足双向关系，不产生问题。
- x-default 完全不参与互指校验。
- 同一有序页面对的重复声明先去重；A 到 B 缺少回指时，无论缺多少种语言，只产生一条 one_way_reciprocal 问题。
- 问题中的页面按站点路径排序。

## x-default 处理

整站所有 HTML 与 sitemap 声明中只要存在一条 x-default，即视为具备兜底。完全不存在时，报告增加一条 missing_x_default 问题，pages 列出所有已知页面。

x-default 只用于兜底检查，不会成为 groups 中的语言标签。

## 主页面选择

CLI 自动读取 --dir 目录下的 hreflang.json。格式为语言标签到配置对象的映射：

    {
      "en": {"primary": "/"},
      "zh-Hans-CN": {"primary": "/cn-b/"}
    }

配置中的语言标签使用同一套归一规则。只有包含多个页面的语言组才需要主页面；配置的路径必须属于该组，否则报错。报告中每个配置过的组有且仅有一个 primary 字段。

## 报告字段

- page_count：发现的 HTML 页面数量，不含 sitemap。
- group_count：非 x-default 语言组数量。
- groups：归一语言标签到组对象的映射；组对象的 pages 是声明该语言标签指向自身的页面，primary 是配置选出的唯一主页面。
- issues：问题列表。每条都包含 type 与 pages；当前类型为 one_way_reciprocal 和 missing_x_default。

## 运行方式

    python -m hreflang.cli --dir demo/pages --out out/report.json

stdout 打印一行摘要，例如：

    pages=9 groups=6 issues=1

测试：

    cd tests
    python -m unittest test_hreflang -v
