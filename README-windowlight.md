# Windowlight Academic ☀︎

一个温柔的、带水彩窗边场景的 **GitHub Pages 个人学术主页**：主页、论文、Peer Review、个人摄影集。代码可直接运行；没有 Node/npm、数据库或后端。构建摄影集预览图时需要 Python Pillow（GitHub Actions 会自动安装）。

> **重要**：本仓库提供的是一份演示站点。`Your Name`、教授姓名、大学、论文、审稿会议/期刊等均为 **占位示例，并非真实履历**。发布前请换成自己的资料，并删除示例论文。

## 1. 五分钟开始

准备 **Python 3.10+**（推荐 3.13）。

```bash
python scripts/build.py
python -m http.server 8000 --directory dist
```

打开 <http://localhost:8000/> 查看主页。其他页面在 `/publications/`、`/peer-review/`、`/photography/`。旧的 `/interests/` 会自动跳转到摄影集。

每次更新内容后，再运行 `python scripts/build.py` 并刷新浏览器即可。`dist/` 是自动生成的目录，不需要手动修改。

> 在 Windows 上如果 `python` 不是有效命令，请改用 `py`。

## 2. 修改自己的资料：只用改少量数据文件

| 我要修改… | 改哪里？ | 备注 |
| --- | --- | --- |
| 姓名、职位、单位、简介 | `data/profile.json` | `bio` 是带链接的文本片段数组 |
| 导师个人主页、知乎链接 | `data/profile.json` | 修改 `bio` 中对应的 `url`，也可修改 `social_links` |
| 个人照片 | `public/assets/my-photo.jpg` | 放入照片后，将 `profile.json` 的 `avatar` 改为 `assets/my-photo.jpg` |
| CV 下载按钮 | `public/assets/cv.pdf` | 放入 PDF 后，将 `profile.json` 的 `cv` 改为 `assets/cv.pdf`；留空则不出现按钮 |
| Publications / preprints | `data/publications/` | 直接增加 `.bib` 或 `.ris`，允许一个文件含多条记录；删除示例文件 |
| 审稿会议/期刊 | `data/reviews.json` | Conference 与 Journal 分开 |
| 摄影作品 | `public/photos/` | 直接添加 JPG / PNG / WebP / AVIF，自动出现在相册中 |
| 摄影作品标题、拍摄日期、地点、相册分类 | `data/photography.json` | 可选。不填写也能展示，只是默认从文件名生成标题 |
| 窗边水彩背景 | `public/assets/window-watercolor.webp` | 替换同名图片即可；推荐宽图、WebP 格式 |
| 主视觉配色和布局 | `public/assets/site.css` | 自定义外观 |

### 带超链接的 bio 语法

编辑 `data/profile.json` 中 `bio` 数组：

```json
"bio": [
  {"text": "I work with "},
  {"text": "Prof. My Advisor", "url": "https://advisor.example.edu/"},
  {"text": ". I write research notes on "},
  {"text": "Zhihu", "url": "https://www.zhihu.com/people/your-id"},
  {"text": "."}
]
```

不带 `url` 的片段仅显示为普通文字；带 `url` 的片段自动成为超链接。所有文本由生成器自动 HTML 转义。

## 3. Photography：只放自己的摄影作品

摄影集地址为 `/photography/`。页面只展示照片，不再按 Travel / Nature / City / Everyday 等类别分组，也没有分类筛选按钮、示例照片或「COLLECTED MOMENTS」栏目。

**浏览者每次刷新页面时，浏览器都会随机打乱全部照片的顺序**（Fisher–Yates shuffle，使用 `Math.random()`）；这一逻辑在网页端运行，而不是在构建时固定排列。关闭 JavaScript 时仍可以浏览照片，只是没有随机排列与放大弹窗。构建时 Pillow 会读取照片的真实尺寸与 EXIF 旋转信息，生成不裁切、保持原图长宽比的轻量 WebP 缩略图，以及更清晰的放大预览图。点按照片可以打开预览，放大窗口中的 Original 链接可查看未经压缩的原图。方向键 `←` / `→` 切换，`Esc` 退出。

### 添加或删除照片

1. 把你自己的 `.jpg`、`.jpeg`、`.png`、`.webp`、`.avif` 文件放到 `public/photos/` 中（支持子文件夹）。
2. 不需要修改 HTML / JavaScript，也不需要给照片分类。照片可使用任意文件名，包括 `IMG_1026.JPG`。
3. 想移除照片，直接删除对应文件即可。
4. 在 GitHub 提交到 `main` 分支后，Actions 会自动构建网站。

`data/photography.json` 中控制上方标题与介绍文字；其中 `photos: []` 表示没有额外元数据，**不会隐藏文件夹中的任何照片**。如需为图片的放大预览添加自定义标题、拍摄地点或说明，可给 `photos` 添加：

```json
{
  "file": "IMG_1026.JPG",
  "title": "Summer afternoon",
  "location": "Singapore",
  "alt": "Sunlight on a quiet street",
  "date": "2026-10-01",
  "orientation": "portrait"
}
```

以上条目是可选元数据，填写时请放在 `photos` 数组内部；不会改变随机顺序或生成分类筛选。缩略图只显示照片，放大时可显示文字信息。缩略图与放大预览会自动根据真实照片宽高（含 EXIF 旋转）保持原始比例，完全不会裁切；不需要手动设置 `orientation`。

**性能提示**：网站会自动为每张照片生成最长边 900px 的 WebP 缩略图和最长边 2200px 的放大预览图，网页不再直接加载十几 MB 的原始 JPG。原图仍保留在 `public/photos/` 中，仅点击 Original 链接时访问。要在本地构建，请先执行 `python -m pip install Pillow`。图片在公开仓库中可被任何人下载，请注意 GPS/EXIF 信息。

---

## 4. Publications：每次扔一个 BibTeX / RIS 即可

将从 Zotero、Google Scholar、Crossref、arXiv 或期刊会议导出的 `.bib` / `.ris` 文件放在 `data/publications/`。**无需手动更改网页和 JSON**。

例如 `data/publications/my-new-paper.bib`：

```bibtex
@inproceedings{my-paper-2026,
  title        = {A Real Paper Title},
  author       = {Doe, Jane and Zhang, Wei},
  booktitle    = {Proceedings of My Conference},
  year         = {2026},
  month        = {oct},
  url          = {https://example.org/my-paper},
  code         = {https://github.com/me/my-code},
  project      = {https://example.org/project},
  pdf          = {https://example.org/paper.pdf},
  featured     = {true},
  highlight    = {First author}
}
```

**支持的自定义字段**：`code`、`pdf`、`project`、`featured` 和 `highlight`。都可省略。`featured = {true}` 的论文会优先进入主页的「Recent publications」列表。`date = {2026-10-12}` 可提供更精确的日期。

RIS 示例：

```ris
TY  - JOUR
TI  - A Real Journal Paper
AU  - Doe, Jane
AU  - Zhang, Wei
PY  - 2026/09/15
JO  - An Actual Journal
DO  - 10.xxxx/your-real-doi
ER  -
```

### 自动处理规则

- **导入**：构建时扫描 `data/publications/` 下所有 `.bib` 和 `.ris`（包括子文件夹）。
- **排序**：优先使用 BibTeX `date` 或 RIS `DA`/`Y1`，否则用 `year` + `month` / `PY`；最新在前。缺少月份时只显示年份，并在同一年月信息更充分的记录之后排序。缺少年份的论文排在末尾。
- **分类**：`@article` / `TY - JOUR` → Journal；`@inproceedings` / `TY - CONF` → Conference；`arXiv` / `@unpublished` / `TY - UNPB` → Preprint；其他情况 → Other。若正式期刊记录同时附带 arXiv 链接，仍归为 Journal。
- **去重**：按标准化标题合并重复导入，同一论文优先保留正式 Journal/Conference 版本。请确保新导出的标题与旧文件一致。
- **链接**：优先读取 `url`、`pdf`、`code`、`project`、`doi`、`eprint`，生成可点击的 Paper/PDF/Code/Project/DOI/arXiv 按钮。
- **交互**：论文列表支持按类别筛选，以及搜索标题、作者、期刊/会议和年份。
- **结构化数据**：构建还会输出 `dist/publications.json`。

目前的解析器为 **Python 标准库实现**，覆盖常见 BibTeX/RIS 导出，支持多条记录、BibTeX 多层花括号、字符串及常见月份缩写、RIS 多行字段。对于特殊 LaTeX 命令、复杂 `crossref` 或非标准日期格式，建议先查看构建输出并检查网页显示；这类边缘情况不承诺完整支持。

## 5. 部署到 GitHub Pages

1. 在 GitHub 新建 **公开仓库**（也可使用你的套餐支持的私有 Pages 仓库）。名称可为 `username.github.io`，或 `academic-homepage` 等普通名字。
2. 将本项目解压后上传到仓库根目录，确保 `.github/workflows/deploy.yml` 也被上传。
3. 打开仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。
4. 将代码提交到 `main`（或 `master`）。进入 **Actions** 查看 `Build and deploy academic homepage` 的运行结果。构建成功后会自动部署。
5. 访问：
   - 仓库名为 `username.github.io`：`https://username.github.io/`
   - 普通项目仓库名为 `academic-homepage`：`https://username.github.io/academic-homepage/`

GitHub Actions 根据仓库名称 **自动配置 base URL**，解决 GitHub 项目页资源路径问题。你每次修改简介或放入新的 BibTeX/RIS 后，只要 Push / Commit，网站就会自动更新。

> 自定义域名：如果绑定自己的域名，可能需要在 workflow 里将 `python scripts/build.py --base ...` 固定为 `--base /`，并在仓库 Settings → Pages 中配置域名。还应配置 `profile.json` 中的 `site_url`（完整站点根 URL，例如 `https://example.com/`）以生成 canonical/sitemap。仅修改 CNAME 文件不等于完成 GitHub Pages 域名配置。

### 上传到 GitHub 的命令示例

```bash
git init
git add .
git commit -m "Create my academic homepage"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

注意将 URL 替换成自己的真实仓库。`dist/` 已由 `.gitignore` 忽略，无需提交。**GitHub 仓库上传文件时，浏览器可能不会自动包含隐藏的 `.github/` 文件夹；建议通过 Git 或 GitHub Desktop 提交完整目录。**

## 6. 项目结构

```text
windowlight-academic/
├── .github/workflows/deploy.yml       # GitHub Pages 自动部署
├── data/
│   ├── profile.json                    # 个人简介、照片、外部链接
│   ├── reviews.json                    # Peer review
│   ├── photography.json                # 摄影作品可选标题、相册和拍摄信息
│   └── publications/
│       ├── 01-sample-conference.bib    # BibTeX 示例
│       └── 02-sample-preprint.ris       # RIS 示例
├── public/photos/                      # 直接放自己拍摄的照片（提供示例占位图）
├── public/assets/
│   ├── window-watercolor.webp          # 水彩背景
│   ├── avatar-placeholder.svg          # 默认占位头像
│   ├── favicon.svg
│   ├── site.css
│   └── site.js
├── scripts/
│   ├── bibliography.py                 # BibTeX/RIS 自动解析 + 日期排序
│   ├── photography.py                  # 摄影集自动扫描、信息整理和日期排序
│   └── build.py                        # 生成四个静态页面
├── templates/layout.html              # 统一 HTML 框架
├── tests/test_site.py                  # 解析/构建测试
└── dist/                               # 构建产物 (gitignore)
```

## 7. 本地验证

```bash
python -m unittest discover -s tests -v
python scripts/build.py
```

预览普通 **GitHub 项目页** 的路径配置：

```bash
python scripts/build.py --base /academic-homepage/
```

本地浏览时将构建结果放入服务器同名路径下才能正确预览该 base；平常本地预览请使用默认 `--base /`。

## 8. 细节与定制

- 没有外部字体请求，正文采用系统字体，标题采用系统衬线字体。
- 风吹纱帘采用极轻的 CSS 动画，并自动遵守系统 `prefers-reduced-motion` 设置。
- 背景使用独立 WebP 插画，头像可换为 `.jpg` / `.png` / `.webp`。
- 页面在手机、平板和桌面有响应式布局；无需任何浏览器框架。
- 索引页和全局 SEO 描述来自 `data/profile.json`；填写 `site_url` 后还会生成 sitemap 与 canonical。
- 首页的精选论文是优先展示 `featured=true` 的文章，不足三篇时用最新的文章补齐。
- 图片及代码作为你的独立站点素材，你可以按需修改本项目的页面和配色。

## 9. 上线前检查

- [ ] 替换 `Your Name` / University / 导师与知乎链接 / 邮箱
- [ ] 上传自己的头像与 CV（CV 可选）
- [ ] **删除两份示例论文**并导入自己的 `.bib` / `.ris`
- [ ] 将 `data/reviews.json` 中的示例审稿经历换成真实记录
- [ ] 删除 `public/photos/demo-*.webp` 示例照片，并添加自己的摄影作品；按需修改 `data/photography.json`
- [ ] 修改 `data/profile.json` 中的 `site_url`，提高 SEO 准确度
- [ ] 部署后检查 Home / Publications / Peer Review / Photography 四页及所有外链

---

Built with warm sunlight, Python, and a fondness for little details. ☁
