import os
import tempfile
import streamlit as st
from pydub import AudioSegment
from streamlit_sortables import sort_items

# ページ設定
st.set_page_config(page_title="CD Crossfade Demo Maker", layout="wide")

# 装飾
st.markdown("""
<style>
    /* 全体背景 */
    .stApp {
        background: linear-gradient(135deg, #f3edf8 0%, #fef7f2 100%);
        color: #4a3b52;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* サイドバー装飾 */
    section[data-testid="stSidebar"] {
        background-color: #f8f2fc !important;
        border-right: 2px solid #e2d4ed;
    }

    /* タイトルとヘッダー */
    h1 {
        color: #7c5295 !important;
        font-weight: 700;
    }
    h2, h3 {
        color: #d97736 !important;
        border-bottom: 1px dashed #e2d4ed;
        padding-bottom: 5px;
    }

    /* ポイントモチーフ */
    .steampunk-decoration {
        font-size: 1.2rem;
        color: #b08ebb;
        margin-right: 8px;
    }

    /* ボタン */
    .stButton>button {
        background: linear-gradient(135deg, #f7a361 0%, #e07a5f 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 10px rgba(224, 122, 95, 0.2);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(224, 122, 95, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown("<h1> クロスフェードエディター改</h1>", unsafe_allow_html=True)
st.caption("XFD Editor ver.2.0")

# 1. パラメータ設定 (サイドバー)
st.sidebar.markdown("### タイム設定")
n = st.sidebar.number_input("1曲あたりの再生時間 (秒): n", min_value=1.0, value=10.0, step=0.5)
m = st.sidebar.number_input("クロスフェード時間 (秒): m", min_value=0.0, value=2.0, step=0.5)

if n <= 2 * m:
    st.sidebar.error("※1曲あたりの再生時間(n)は、クロスフェード時間(m)の2倍より大きく設定してください")

p = (n / 2) + (m / 2)
p_minus_2m = p - (2 * m)

st.sidebar.markdown("---")
st.sidebar.markdown("### 計算結果")
st.sidebar.caption(f"・頭/末尾切り出し長 (p): `{p:.2f}` 秒")
st.sidebar.caption(f"・中盤単独再生長: `{p_minus_2m:.2f}` 秒")

# 2. ファイルアップロード
st.markdown("## 1. 音声ファイルのアップロード")
uploaded_files = st.file_uploader(
    "MP3, WAVなどの音声ファイルを複数選択してください", 
    type=["mp3", "wav", "m4a", "ogg", "flac"], 
    accept_multiple_files=True
)

if uploaded_files:
    # ファイル名リストの保持
    file_dict = {f.name: f for f in uploaded_files}
    
    # セッション状態初期化（アップロード時の順序保持）
    if "song_order" not in st.session_state or set(st.session_state.song_order) != set(file_dict.keys()):
        st.session_state.song_order = list(file_dict.keys())

    # ① ドラッグ＆ドロップによる並べ替えリスト
    st.markdown("## 2. 曲順の編集（ドラッグ＆ドロップ）")
    st.caption("以下のリスト項目を自由にドラッグ＆ドロップして並べ替え")

    # sort_items で並べ替え可能なUIを表示
    sorted_order = sort_items(st.session_state.song_order)
    st.session_state.song_order = sorted_order

    if sorted_order and n > 2 * m:
        st.markdown("## 3. デモトラックの作成")
        
        if st.button("クロスフェードデモを作成する"):
            with st.spinner("音声処理を実行中..."):
                try:
                    n_ms = int(n * 1000)
                    m_ms = int(m * 1000)
                    p_ms = int(p * 1000)

                    parts = []
                    
                    # 結合用のAudioSegmentおよび個別トラック保持用
                    for name in sorted_order:
                        uploaded_file = file_dict[name]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name

                        audio = AudioSegment.from_file(tmp_path)
                        os.remove(tmp_path)

                        part1 = audio[:p_ms]
                        part2 = audio[-p_ms:] if len(audio) >= p_ms else audio
                        parts.append((name, part1, part2))

                    # デモ全体の作成と、つなぎ目ごとの切り出し処理
                    demo_track = AudioSegment.empty()
                    
                    # 同一トラック内（Part1とPart2）のクロスフェード結合後の1曲分の実効長
                    # L = p + p - m = 2p - m （秒換算で n 秒相当）
                    single_track_len_ms = (2 * p_ms) - m_ms

                    for i, (name, p1, p2) in enumerate(parts):
                        # 同一トラック内の頭(A1)と末尾(A2)はクロスフェードで接続
                        track_segment = p1.append(p2, crossfade=m_ms)
                        
                        # トラック間（曲A ➔ 曲B）はクロスフェードせずそのまま繋ぐ
                        if i == 0:
                            demo_track = track_segment
                        else:
                            demo_track = demo_track.append(track_segment, crossfade=0)

                    # 出力保存
                    output_io = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    demo_track.export(output_io.name, format="mp3")
                    st.session_state.demo_file_path = output_io.name

                    # つなぎ目プレビュー用データの生成
                    # 各「曲と曲の境目」前後（トラック間のカット接続部分）を切り出す
                    transitions = []
                    for i in range(len(parts) - 1):
                        curr_name = parts[i][0]
                        next_name = parts[i+1][0]
                        
                        # 境目のタイムスタンプ計算（トラック間はクロスフェードしないため単に1曲の長さの倍数）
                        transition_center_ms = (i + 1) * single_track_len_ms
                        
                        # 前後3秒（計6秒）をつなぎ目試聴用に切り出し
                        start_ms = max(0, transition_center_ms - 3000)
                        end_ms = min(len(demo_track), transition_center_ms + 3000)
                        
                        clip = demo_track[start_ms:end_ms]
                        
                        clip_io = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        clip.export(clip_io.name, format="mp3")
                        transitions.append((f"トラック {i+1} ({curr_name}) ➔ トラック {i+2} ({next_name})", clip_io.name))

                    st.session_state.transitions = transitions
                    st.success("クロスフェードデモができました！")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

        # 生成結果の表示
        if "demo_file_path" in st.session_state and os.path.exists(st.session_state.demo_file_path):
            st.markdown("### フルデモトラック試聴")
            st.audio(st.session_state.demo_file_path, format="audio/mp3")

            with open(st.session_state.demo_file_path, "rb") as f:
                st.download_button(
                    label="生成されたデモトラックをダウンロード (.mp3)",
                    data=f,
                    file_name="crossfade_demo.mp3",
                    mime="audio/mp3"
                )

            # ピンポイント繋ぎ目試聴セクション
            if "transitions" in st.session_state and st.session_state.transitions:
                st.markdown("---")
                st.markdown("## 3. ピンポイント試聴")
                st.caption("曲と曲が切り替わるクロスフェード部分、及びその前後3秒だけをピンポイントで確認できます。")

                selected_trans_label = st.selectbox(
                    "確認したい繋ぎ目を選択してください：",
                    options=[t[0] for t in st.session_state.transitions]
                )

                for label, clip_path in st.session_state.transitions:
                    if label == selected_trans_label:
                        st.audio(clip_path, format="audio/mp3")
