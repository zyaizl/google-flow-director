# Google Flow (Veo) Commercial Cinematography & Prompt Library

This reference consolidates proven commercial video prompt structures and visual quality standards adapted from `HiAPIAI/awesome-ai-video-workflows`, `creatify-ai/video-ad-generator`, `KunLabAI/KunFlix`, and `BigBanana-AI-Director`.

---

## 1. Global Visual Bible Templates (Suffix Locks)

Every shot in a single project MUST append an identical **Global Style Suffix** to guarantee multi-clip visual consistency across Google Flow generations.

### 1.1 City & Cultural Tourism (城市文旅宣传片)
- **Oriental Poetic & Cinematic (东方美学/电影感)**
  - `Shot on ARRI Alexa 65, Panavision Primo 70 anamorphic lens, 35mm film grain, Kodak Vision3 500T, atmospheric volumetric mist, warm golden hour rim lighting contrasting with deep cyan shadows, cinematic color grading, ultra-detailed textures, photorealistic, 8k, smooth gimbal movement.`
- **Cyberpunk / Modern Metropolis (现代都市/赛博流光)**
  - `Shot on RED V-Raptor 8K VV, Cooke Anamorphic /i Special Flare lens, neon reflections on wet asphalt, high-contrast teal and amber color palette, crisp architectural lines, dynamic time-lapse energy, anamorphic lens flare, ultra-sharp, commercial film look.`
- **Natural Epic & Documentary (山河史诗/国家地理质感)**
  - `Shot on IMAX 70mm camera, Zeiss Master Prime lenses, natural diffused sunlight, Tyndall effect light rays piercing through clouds, rich organic earth tones, pristine water and foliage textures, sweeping aerial drone stability, National Geographic cinematography.`

### 1.2 Brand TVC (品牌情绪大片)
- **Luxury & Minimalist (高奢极简/静奢风)**
  - `Shot on Sony Venice 2, Leica Thalia lenses, soft diffused studio butterfly lighting, muted neutral palette with warm champagne highlights, shallow depth of field (f/1.4), creamy bokeh, tactile fabric and skin textures, A24 meets luxury fashion house commercial aesthetic.`
- **Warm Humanistic & Lifestyle (温暖人文/生活质感)**
  - `Shot on Arriflex 416 16mm film camera, natural window sunlight with floating dust motes, warm nostalgic Fuji Eterna film emulation, intimate handheld breathing motion, authentic skin tones, soft halation on highlights, emotional commercial storytelling.`

### 1.3 Product Hero Showcase (产品高光展示)
- **Tech & Precision Hardware (数码科技/精密工业)**
  - `Shot on Phantom Flex4K high-speed camera, Laowa 24mm f/14 Probe Macro lens, sleek dark obsidian studio environment, programmable motorized rim light sweeping across anodized aluminum and glass surfaces, razor-sharp reflections, CGI-level photorealism, Apple product launch cinematography.`
- **Beauty, Fragrance & Beverage (美妆香氛/饮品水花)**
  - `Shot on Phantom Flex4K at 1000fps slow motion, 100mm macro lens, backlit caustic light refraction through crystal glass, micro water droplets suspended in mid-air, lush botanical or silk background, vibrant high-key commercial lighting, crisp specular highlights.`

---

## 2. Transition Bridge Taxonomy (镜头无缝转场矩阵)

Because Google Flow generates 5s–8s clips (or up to 15s via Extend), seamless transitions between separate clips rely on matching **Exit Momentum (上一镜尾)** and **Entry Momentum (下一镜首)**.

| Transition Code | Name (中文/EN) | Shot N Tail Action (上一镜结尾提示词) | Shot N+1 Head Action (下一镜开头提示词) | Best Used For |
| :--- | :--- | :--- | :--- | :--- |
| **`MATCH_SHAPE`** | 图形匹配转场 (Graphic Match Cut) | `Camera pushes in tightly until [circular/geometric object] fills the entire center frame, holding symmetry.` | `Starts tightly framed on a matching [circular/geometric subject] in the same center position, then camera smoothly pulls back to reveal [new scene].` | 城市文旅（古今建筑/器物与地标跨越）、品牌联想 |
| **`WHIP_WIPE`** | 甩镜遮罩转场 (Whip Pan / Foreground Wipe) | `At the end of the shot, camera executes a rapid whip pan right, passing closely behind a dark foreground [pillar/tree/silhouette] that momentarily fills the frame in motion blur.` | `Camera emerges from behind a dark foreground silhouette in a fast whip pan right, settling smoothly into a steady view of [new scene].` | 空间快速切换、节奏提速段 |
| **`SPEED_RAMP_DIVE`** | 极速穿云/微距穿入 (Speed-Ramp Dive) | `Camera accelerates forward in a dramatic speed-ramp, diving directly into the dark center/reflective surface of [object/cloud/water].` | `Camera emerges forward out of shimmering [water ripples/mist/metallic reflection], decelerating into a smooth glide over [new scene].` | 产品内部结构穿梭、航拍穿云转地面 |
| **`LIGHT_BOKEH`** | 光斑失焦/眩光转场 (Light Leak & Rack Focus) | `Camera racks focus out as warm golden sunlight/neon light flares flood the lens, dissolving the image into creamy glowing bokeh orbs.` | `Starts completely out of focus with glowing golden bokeh orbs filling the frame, then smoothly racks focus into sharp detail on [subject].` | 情绪升华、昼夜交替、时间流逝 |
| **`MOTION_RELAY`** | 动势接力转场 (Directional Motion Continuity) | `Subject/Light beam moves steadily from left to right across the frame as camera tracks right at matching speed.` | `Camera continues tracking left-to-right at the exact same speed, picking up [new subject/light stream] moving in the same trajectory.` | 产品多角度连续展示、多地标巡礼 |
| **`SCENE_EXTEND`** | Flow 原生延展 (Flow SceneBuilder Extend) | `Camera maintains a continuous uninterrupted movement without hard cuts, settling onto a clear composition ready for extension.` | `Use Google Flow SceneBuilder -> Extend (+5s~8s) from previous clip's final second, shifting camera angle from [A] to [B].` | 单一宏大场景长镜头、一镜到底 |

---

## 3. Generation Mode Decision Rules (何时纯文生 vs 何时首尾帧/垫图)

To keep the workflow fast while preventing AI hallucination:

1. **`[T2V 純文生]` (Default — ~70% of shots)**
   - **When to use**: Atmospheric landscapes, cityscapes, crowd energy, environmental B-roll, abstract macro textures (water, fire, silk, mist), transitions where shape/motion matters more than exact logo geometry.
   - **How to keep consistency**: Inject the exact **Global Visual Bible Suffix** + explicit color palette + lighting direction into every prompt.
2. **`[I2V 首帧垫图 / Ingredients]` (Targeted — ~20% of shots)**
   - **When to use**: Any shot featuring the **exact commercial product SKU** (packaging, bottle, hardware ports, brand logo) or a specific **iconic landmark** that T2V might distort.
   - **Workflow**: Upload the real product photo (or AI-generated Hero Anchor image) into Google Flow's **Ingredients / Start Frame**, then use the Motion Prompt to drive lighting and camera movement around the locked subject.
3. **`[F2V 首尾帧桥接]` (High-Precision Morph — ~10% of shots)**
   - **When to use**: A signature "impossible transition" (e.g., ancient clay porcelain morphing into a modern skyscraper, or raw ingredients assembling into the final product bottle).
   - **Workflow**: Use Shot N's last frame (or generated Anchor Frame A) as Start Frame, and Shot N+1's target composition (Anchor Frame B) as End Frame in Google Flow.

---

## 4. Google Flow (Veo) Native Audio, Voiceover & Subtitle Prompting (音画配音一体化规范)

Google Flow natively generates synchronized **Voiceover (旁白/人声)**, **Foley/SFX (动作环境音效)**, **Background Music (BGM)**, and **On-screen Typography/Subtitles (字幕/落版字)** directly from the video prompt.

To prevent the narrator's voice from changing between Clip 1 and Clip 2, every project MUST define a **Global Voice & Audio Lock (`voice_and_audio_lock_en`)** alongside the Global Visual Suffix, and embed audio/voice/subtitle instructions directly into every shot's `flow_video_prompt_en`.

### 4.1 Global Voice & Audio Locks (跨镜头配音音色锁)

- **Oriental Cultural & Documentary Narrator (人文纪录片/文旅磁性旁白)**
  - `Audio Lock: Consistent warm, deep, resonant male Mandarin Chinese narrator voice (CCTV documentary style, calm poetic cadence, crisp studio condenser mic), accompanied by ethereal Guqin harmonics and deep cinematic cello score.`
- **Luxury Brand TVC Narrator (高奢品牌/静奢风女声旁白)**
  - `Audio Lock: Consistent intimate, velvety, sophisticated female Mandarin Chinese voiceover (calm luxury brand ambassador tone, gentle breathy texture, slow deliberate pacing), backed by minimalist ambient piano and warm analog synth pad.`
- **Tech & Product Launch Narrator (科技数码/现代极客旁白)**
  - `Audio Lock: Consistent crisp, confident, modern mid-range Mandarin Chinese narrator voice (Apple keynote commercial cadence, clean articulation), paired with precision high-tech foley sound design and deep sub-bass pulse.`

### 4.2 Standard All-in-One Prompt Structure for Google Flow

Every `flow_video_prompt_en` MUST weave Visuals, Camera, Native Voiceover, Synchronized SFX/Music, and Subtitle cues into one cohesive prompt block ready to paste into Google Flow:

```text
[Visual & Camera]: <Detailed continuous camera movement and visual action across the timeline...>
[Native Audio & SFX]: Synchronized high-fidelity foley sound of <specific actions at specific moments>, blending with <BGM style and emotional progression>.
[Voiceover]: A consistent <Voice Lock Profile> speaks in clear, standard Mandarin Chinese: "<Exact Chinese VO Script>".
[Subtitles & On-Screen Text]: <Optional clean cinematic subtitles at bottom center reading "<Text>" / or Final title card overlay reading "<Brand Slogan>">.
[Global Visual Lock]: <Exact Global Style Suffix>
```
