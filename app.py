import os
import tempfile
import streamlit as st
from pydub import AudioSegment

st.set_page_config(page_title="CDクロスフェードデモ作成ツール", layout="wide")

st.title("🎵 CDクロスフェードデモ作成ツール")
st.write("複数の音源をアップロードし、各曲の切り出し・クロスフェード設定をして1つのデモトラックを作成します。")

# 1. パラメータ設定 (サイドバー)
st.sidebar.header("⚙️ 設定")
n = st.sidebar.number_input("1曲あたりの再生時間 (秒): n", min_value=1.0, value=10.0, step=0.5)
m = st.sidebar.number_input("クロスフェード時間 (秒): m", min_value=0.0, value=2.0, step=0.5)

# バリデーションチェック
if n <= 2 * m:
    st.sidebar.error("⚠️ 1曲あたりの再生時間(n)は、クロスフェード時間(m)の2倍より大きく設定してください。")

# ロジック計算: p = n/2 + m/2
p = (n / 2) + (m / 2)
p_minus_2m = p - (2 * m)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 計算パラメータ（自動）")
st.sidebar.caption(f"・各曲の頭/末尾切り出し長 (p): `{p:.2f}` 秒")
st.sidebar.caption(f"・A2単独再生パート長 (p - 2m): `{p_minus_2m:.2f}` 秒")

# 2. ファイルアップロード
st.header("1. 音声ファイルのアップロード")
uploaded_files = st.file_uploader(
    "MP3, WAVなどの音声ファイルを複数選択してください", 
    type=["mp3", "wav", "m4a", "ogg", "flac"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.header("2. 曲順の設定")
    
    file_names = [f.name for f in uploaded_files]
    file_dict = {f.name: f for f in uploaded_files}
    
    selected_order = st.multiselect(
        "デモに含める曲と順序を選択してください",
        options=file_names,
        default=file_names
    )

    if selected_order and n > 2 * m:
        st.header("3. デモトラックの作成")
        if st.button("🚀 クロスフェードデモを生成する"):
            with st.spinner("音声処理中..."):
                try:
                    n_ms = int(n * 1000)
                    m_ms = int(m * 1000)
                    p_ms = int(p * 1000)

                    parts = []

                    for name in selected_order:
                        uploaded_file = file_dict[name]
                        # 一時ファイルとして読み込み
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name

                        audio = AudioSegment.from_file(tmp_path)
                        os.remove(tmp_path)

                        # Part1: 頭から p 秒間
                        part1 = audio[:p_ms]
                        # Part2: 末尾から p 秒間
                        part2 = audio[-p_ms:] if len(audio) >= p_ms else audio

                        parts.append((part1, part2))

                    demo_track = AudioSegment.empty()

                    for i, (p1, p2) in enumerate(parts):
                        if i == 0:
                            demo_track = p1.append(p2, crossfade=m_ms)
                        else:
                            demo_track = demo_track.append(p1, crossfade=m_ms)
                            demo_track = demo_track.append(p2, crossfade=m_ms)

                    output_io = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    demo_track.export(output_io.name, format="mp3")

                    st.success("✨ デモトラックの生成が完了しました！")
                    st.audio(output_io.name, format="audio/mp3")

                    with open(output_io.name, "rb") as f:
                        st.download_button(
                            label="💾 生成されたデモトラックをダウンロード (.mp3)",
                            data=f,
                            file_name="crossfade_demo.mp3",
                            mime="audio/mp3"
                        )
                    os.remove(output_io.name)

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")