import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from openai import OpenAI
import os
import json
import time

# API 키 기본값은 빈 문자열
DEFAULT_OPENAI_API_KEY = ""

st.set_page_config(
    page_title="BlogClip",
    page_icon="🎬",
    layout="wide"
)

def extract_text_from_pdf(uploaded_file):
    """업로드된 PDF에서 텍스트 추출"""
    try:
        # 임시 파일로 저장
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # PyPDFLoader로 텍스트 추출
        loader = PyPDFLoader("temp.pdf")
        pages = loader.load()
        text = "\n".join([page.page_content for page in pages])
        
        # 임시 파일 삭제
        os.remove("temp.pdf")
        return text
    except Exception as e:
        st.error(f"PDF 읽기 오류: {e}")
        return ""

def generate_video_script(text, script_length=1000, model="gpt-4-turbo-preview"):
    """GPT를 활용하여 블로그 제작을 위한 스크립트 생성"""
    if not text:
        return "스크립트를 생성할 내용이 없습니다."
    
    prompt = f"""
    다음 문서의 내용을 바탕으로 약 {script_length}자 내외의 블로그 페이지 제작을 위한 스크립트를 작성해 주세요.
    각 페이지별로 아래 형식을 따라주세요:
    
    # 페이지 제목: [제목]
    
    ## 페이지 스크립트:
    [상세 설명 스크립트]
    
    각 페이지별로 고객 대상으로 친절한 어투로 자세한 설명을 제공해 주세요.
    
    문서 내용:
    {text}
    """
    try:
        # API 키 가져오기
        api_key = st.session_state.get('openai_api_key', DEFAULT_OPENAI_API_KEY)
        client = OpenAI(api_key=api_key)
        
        with st.spinner('블로그 스크립트 생성 중...'):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "당신은 블로그 제작 전문가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"스크립트 생성 오류: {e}")
        return "블로그 스크립트 생성 실패"

def generate_image_prompts(script, model="gpt-4-turbo-preview"):
    """각 블로그 페이지별로 개별적인 이미지 생성 프롬프트 생성 (실사 스타일)"""
    if not script:
        return []
    
    prompt = f"""
    아래 블로그 페이지의 스크립트를 분석하여,
    각 페이지를 초고화질 실사 사진처럼 표현할 수 있는 세부적이고 자세한 이미지 생성 프롬프트를 만들어 주세요.
    
    프롬프트는 다음과 같은 요소를 포함해야 합니다:
    1. 주요 피사체의 명확한 설명 (인물, 제품, 환경 등)
    2. 조명 조건 (자연광, 부드러운 조명, 극적인 조명 등)
    3. 촬영 각도 및 구도 (클로즈업, 전체 샷, 원근감 등)
    4. 색감 및 분위기 (밝고 활기찬, 차분하고 따뜻한 등)
    5. 고급 사진 효과 (얕은 심도, 선명한 디테일, 부드러운 배경 등)
    
    결과는 반드시 유효한 JSON 형식의 리스트로 반환해주세요. 예:
    [
      "첫 번째 페이지를 위한 상세한 이미지 프롬프트",
      "두 번째 페이지를 위한 상세한 이미지 프롬프트"
    ]
    장면을 5개로 제한해 주세요.
    
    스크립트:
    {script}
    """
    try:
        # API 키 가져오기
        api_key = st.session_state.get('openai_api_key', DEFAULT_OPENAI_API_KEY)
        client = OpenAI(api_key=api_key)
        
        with st.spinner('이미지 프롬프트 생성 중...'):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "당신은 안전하고 정교하며 사실적인 이미지 생성 프롬프트를 작성하는 전문가입니다. 항상 유효한 JSON 형식으로 응답하세요."},
                    {"role": "user", "content": prompt}
                ]
            )
        content = response.choices[0].message.content.strip()
        
        # 응답에서 JSON 부분만 추출 시도
        try:
            # JSON 시작과 끝 찾기 (대괄호 기준)
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # JSON 형식이 아니면 줄바꿈으로 분리하여 리스트 생성
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith(('```', '[', ']', '{', '}'))]
                if len(lines) > 0:
                    return lines[:5]  # 최대 5개의 프롬프트만 사용
                else:
                    return ["실사 스타일의 사실적인 장면"]  # 기본 프롬프트 반환
        except json.JSONDecodeError:
            # 비상 대책: 간단한 프롬프트 리스트 반환
            return ["실사 스타일의 사실적인 장면", "사실적이며 정교한 장면"]
            
    except Exception as e:
        st.error(f"이미지 프롬프트 생성 오류: {e}")
        return ["실사 스타일의 사실적인 장면"]  # 기본 프롬프트 반환

def generate_images(image_prompts, image_style="실사 스타일"):
    """DALL·E를 활용하여 각 이미지 프롬프트에 대한 이미지 생성"""
    if not image_prompts:
        return []
    
    # 이미지 스타일에 따른 스타일 지시 문구
    style_prompts = {
        "실사 스타일": " Create a hyper-realistic photograph with extreme detail. Use professional photography techniques with natural lighting, perfect focus, and authentic textures. The image should look indistinguishable from a high-end camera photo with 8K resolution. Include subtle details like skin pores, fabric texture, or surface reflections where appropriate. Use photorealistic color grading with naturalistic environment.",
        "동화책 스타일": " in a soft, illustrated storybook style, warm and cozy colors.",
        "수채화 스타일": " as a delicate watercolor painting with soft colors and gentle brushstrokes.",
        "3D 렌더링": " as a colorful 3D rendered scene with soft lighting and gentle shadows.",
        "일러스트레이션": " as a clean, modern illustration with vibrant colors and simple shapes."
    }
    
    # 기본 스타일 설정
    style_prompt = style_prompts.get(image_style, style_prompts["실사 스타일"])
    
    # API 키 가져오기
    api_key = st.session_state.get('openai_api_key', DEFAULT_OPENAI_API_KEY)
    client = OpenAI(api_key=api_key)
    
    image_urls = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, prompt in enumerate(image_prompts[:5]):  # 최대 5개의 이미지만 생성
        try:
            status_text.text(f"이미지 {i+1}/{min(len(image_prompts), 5)} 생성 중...")
            progress_bar.progress((i) / min(len(image_prompts), 5))
            
            # 문자열 타입 확인 및 변환
            if isinstance(prompt, dict) and 'prompt' in prompt:
                prompt_text = prompt['prompt']
            else:
                prompt_text = str(prompt)  # 문자열로 변환
                
            full_prompt = prompt_text + style_prompt
            
            response = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                n=1,
                size="1024x1024"
            )
            image_urls.append({
                'prompt': prompt_text,
                'url': response.data[0].url
            })
            time.sleep(1)  # API 호출 제한 방지
        except Exception as e:
            st.error(f"이미지 {i+1} 생성 오류: {str(e)}")
            image_urls.append({
                'prompt': prompt if isinstance(prompt, str) else str(prompt),
                'url': None
            })
    
    progress_bar.progress(1.0)
    status_text.text("이미지 생성 완료!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return image_urls

# 다운로드 처리 함수만 유지
# HTML 링크 생성 함수는 불필요하므로 제거

# 다운로드 함수
def download_file(content, filename):
    """파일 다운로드 처리 - 상태 초기화 방지"""
    st.session_state.download_clicked = True
    st.success(f"'{filename}' 다운로드가 시작되었습니다!")

def main():
    st.title("📚 BlogClip🎬")
    st.subheader("PDF를 스크립트와 멋진 이미지 시퀀스로 변환하세요")
    
    # 세션 상태 초기화
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""
    
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "gpt-4-turbo"
    
    if 'processing_done' not in st.session_state:
        st.session_state.processing_done = False
    
    if 'script' not in st.session_state:
        st.session_state.script = ""
    
    if 'image_prompts' not in st.session_state:
        st.session_state.image_prompts = []
    
    if 'image_results' not in st.session_state:
        st.session_state.image_results = []
    
    if 'download_clicked' not in st.session_state:
        st.session_state.download_clicked = False
    
    # 사이드바에 API 키 입력 및 모델 선택 추가
    with st.sidebar:
        st.header("설정")
        
        # API 키 입력
        api_key_input = st.text_input(
            "OpenAI API 키", 
            value=st.session_state.openai_api_key,
            type="password",
            help="OpenAI API 키를 입력하세요. 이전에 입력한 경우 자동으로 불러옵니다."
        )
        
        # 입력값 저장
        if api_key_input:
            st.session_state.openai_api_key = api_key_input
        
        # LLM 모델 선택
        st.subheader("LLM 모델 선택")
        selected_model = st.selectbox(
            "사용할 모델",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            index=2,  # 기본값으로 gpt-4-turbo 선택
            help="텍스트 생성에 사용할 OpenAI 모델을 선택하세요."
        )
        
        # 모델 선택 저장
        st.session_state.selected_model = selected_model
        
        st.divider()
        
        st.header("PDF 업로드")
        uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")
        
        if uploaded_file is not None:
            st.success("PDF 업로드 완료!")
            st.image("https://cdn-icons-png.flaticon.com/512/337/337946.png", width=100)
            
            # 설정 옵션
            st.subheader("옵션 설정")
            script_length = st.slider("스크립트 길이 (자)", 100, 3000, 1000, 100)
            image_style = st.selectbox(
                "이미지 스타일",
                ["실사 스타일", "동화책 스타일", "수채화 스타일", "3D 렌더링", "일러스트레이션"]
            )
            
            # API 키 확인
            if not st.session_state.openai_api_key:
                st.warning("OpenAI API 키를 입력해주세요.")
                process_button = False
            else:
                # 처리 시작 버튼
                process_button = st.button("✨ 변환 시작", use_container_width=True)
                
                # 버튼 클릭 시 세션 상태 초기화
                if process_button:
                    st.session_state.processing_done = False
                    st.session_state.script = ""
                    st.session_state.image_prompts = []
                    st.session_state.image_results = []
        else:
            process_button = False
            st.info("먼저 PDF 파일을 업로드해주세요.")
            st.markdown("""
            ### 사용 방법
            1. OpenAI API 키를 입력하세요
            2. 사용할 LLM 모델을 선택하세요
            3. PDF 파일을 업로드하세요
            4. 스크립트 길이와 이미지 스타일을 선택하세요
            5. '변환 시작' 버튼을 클릭하세요
            6. 결과를 확인하고 다운로드하세요
            """)
    
    # 메인 섹션
    if uploaded_file is not None and (process_button or st.session_state.processing_done):
        # 처리가 완료되지 않았거나 새로운 처리 요청이 있을 경우에만 실행
        if not st.session_state.processing_done or process_button:
            # 진행 상황 표시 컨테이너
            progress_container = st.container()
            with progress_container:
                text = extract_text_from_pdf(uploaded_file)
                if not text:
                    st.error("PDF에서 텍스트를 추출할 수 없습니다.")
                    return
                
                # 선택된 모델로 스크립트 생성
                selected_model = st.session_state.selected_model
                script = generate_video_script(text, script_length, selected_model)
                if not script or "실패" in script:
                    st.error("블로그 스크립트 생성에 실패했습니다.")
                    return
                
                # 세션에 스크립트 저장
                st.session_state.script = script
                
                # 선택된 모델로 이미지 프롬프트 생성
                image_prompts = generate_image_prompts(script, selected_model)
                if not image_prompts:
                    st.error("이미지 프롬프트 생성에 실패했습니다.")
                    return
                
                # 세션에 이미지 프롬프트 저장
                st.session_state.image_prompts = image_prompts
                
                # 선택한 이미지 스타일 전달
                image_results = generate_images(image_prompts, image_style)
                
                # 세션에 이미지 결과 저장
                st.session_state.image_results = image_results
                
                # 처리 완료 상태 업데이트
                st.session_state.processing_done = True
        
        # 결과 표시 (처리 완료 상태일 때)
        if st.session_state.processing_done:
            # 탭으로 결과 보기 옵션
            tab1, tab2 = st.tabs(["📊 생성 결과", "🖼️ 이미지 갤러리"])
            
            with tab1:
                # 3열 레이아웃으로 결과 표시
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### 📝 블로그 스크립트")
                    st.text_area("스크립트", st.session_state.script, height=500)
                    
                    # 다운로드 버튼
                    st.download_button(
                        "스크립트 다운로드",
                        st.session_state.script,
                        file_name="video_script.txt",
                        mime="text/plain",
                        on_click=download_file,
                        args=(st.session_state.script, "video_script.txt"),
                        key="script_download"
                    )
                
                with col2:
                    st.markdown("### 🎨 이미지 프롬프트")
                    for i, prompt in enumerate(st.session_state.image_prompts[:5]):
                        # 프롬프트가 딕셔너리인 경우 확인
                        if isinstance(prompt, dict) and 'prompt' in prompt:
                            display_prompt = prompt['prompt']
                        else:
                            display_prompt = str(prompt)
                        st.text_area(f"페이지 프롬프트 {i+1}", display_prompt, height=80, key=f"prompt_{i}")
                    
                    # 이미지 프롬프트 리스트를 문자열로 변환
                    prompt_json = json.dumps(
                        [p['prompt'] if isinstance(p, dict) and 'prompt' in p else str(p) for p in st.session_state.image_prompts],
                        indent=2, 
                        ensure_ascii=False
                    )
                    
                    # 다운로드 버튼
                    st.download_button(
                        "프롬프트 다운로드",
                        prompt_json,
                        file_name="image_prompts.json",
                        mime="application/json",
                        on_click=download_file,
                        args=(prompt_json, "image_prompts.json"),
                        key="prompt_download"
                    )
                
                with col3:
                    st.markdown("### 🖼️ 생성된 이미지")
                    for i, img_data in enumerate(st.session_state.image_results):
                        if img_data['url']:
                            st.markdown(f"**장면 {i+1}**")
                            st.image(img_data['url'], use_container_width=True)
                        else:
                            st.error(f"장면 {i+1} 이미지 생성 실패")
            
            with tab2:
                # 이미지 갤러리 뷰 (더 크게 표시)
                st.markdown("### 📸 이미지 갤러리")
                
                # 두 열로 이미지 배치
                for i in range(0, len(st.session_state.image_results), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i+j < len(st.session_state.image_results) and st.session_state.image_results[i+j]['url']:
                            with cols[j]:
                                st.image(st.session_state.image_results[i+j]['url'], caption=f"장면 {i+j+1}", use_container_width=True)
                                st.markdown(f"**프롬프트:** {st.session_state.image_results[i+j]['prompt'][:100]}...")
                
                # 전체 결과 다운로드 옵션
                st.markdown("### 📥 전체 결과 다운로드")
                
                # 결과를 JSON으로 변환
                result_data = {
                    "script": st.session_state.script,
                    "image_prompts": [
                        p['prompt'] if isinstance(p, dict) and 'prompt' in p else str(p) 
                        for p in st.session_state.image_prompts
                    ],
                    "image_urls": [img['url'] for img in st.session_state.image_results]
                }
                
                result_json = json.dumps(result_data, indent=2, ensure_ascii=False)
                
                # 다운로드 버튼
                st.download_button(
                    "전체 결과 JSON 다운로드",
                    result_json,
                    file_name="video_creation_results.json",
                    mime="application/json",
                    on_click=download_file,
                    args=(result_json, "video_creation_results.json"),
                    key="result_download"
                )
        
        # 다운로드 성공 메시지 표시
        if st.session_state.download_clicked:
            st.success("파일이 성공적으로 다운로드되었습니다!")
            # 다음 다운로드를 위해 상태 재설정
            st.session_state.download_clicked = False

if __name__ == "__main__":
    main()
