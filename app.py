import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="청취담 연합파티 매칭 V2", page_icon="🍻", layout="wide")

# ==========================================
# [보안] 관리자 로그인 시스템
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 관리자 로그인")
    st.info("스케줄러에 접근하려면 비밀번호를 입력해주세요.")
    pwd = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd == "1234":
            st.session_state["authenticated"] = True
            st.rerun() 
        else:
            st.error("⚠️ 비밀번호가 틀렸습니다.")
    st.stop()
# ==========================================

st.title("🍻 청취담 연합파티 스케줄러 V2")
st.markdown("**참가자 선발부터 자리 배치, 결과 리포트까지 완벽하게 통합된 시스템입니다.**")

# 3단계 프로세스 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 Step 1: 참가자 선발", "🔀 Step 2: 자리 배치 (진행 예정)", "📊 Step 3: 사후 리포트 (진행 예정)"])

# ==========================================
# TAB 1: 참가자 선발 시스템
# ==========================================
with tab1:
    st.header("🎯 파티 참가자 자동 선발 및 대기자 관리")
    st.write("모집된 전체 신청자 명단을 업로드하면, 정원과 조건에 맞게 최종 참가자와 대기자를 분리합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        total_capacity = st.number_input("이번 파티 총 정원 (명)", min_value=4, value=100, step=4)
    with col2:
        st.info("💡 남녀 5:5 비율을 목표로 하되, 한쪽 성별이 부족하면 전체 정원에 맞춰 반대쪽 성별을 추가 선발합니다.")

    st.write("---")
    
    # 파일 업로드 (현재 신청자 & 과거 대기자)
    col3, col4 = st.columns(2)
    with col3:
        current_file = st.file_uploader("📂 [필수] 이번 파티 전체 신청자 명단 (엑셀/CSV)", type=['xlsx', 'csv'], key="current")
    with col4:
        past_waitlist_file = st.file_uploader("📂 [선택] 저번 파티 대기자/미선정자 명단 (엑셀/CSV)", type=['xlsx', 'csv'], key="past")

    if current_file is not None:
        # 데이터 읽기
        if current_file.name.endswith('.csv'):
            df_current = pd.read_csv(current_file)
        else:
            df_current = pd.read_excel(current_file)
            
        # 컬럼명 동적 정제
        target_keywords = ['이름', '성별', '소속학교', '학과', '학년', '참여이력', '신규']
        rename_dict = {}
        for keyword in target_keywords:
            matched_col = next((col for col in df_current.columns if keyword in str(col)), None)
            if matched_col and matched_col != keyword:
                if keyword == '신규': rename_dict[matched_col] = '참여이력'
                else: rename_dict[matched_col] = keyword
        if rename_dict: df_current = df_current.rename(columns=rename_dict)

        # 필수 컬럼 검증
        if not {'이름', '성별', '소속학교'}.issubset(df_current.columns):
            st.error("⚠️ 파일 첫 줄에 최소한 '이름', '성별', '소속학교' 가 포함되어야 합니다.")
        else:
            # 데이터 정제
            df_current['성별'] = df_current['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
            df_current['소속학교'] = df_current['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
            
            # 참여이력(신규/크루) 컬럼 처리
            if '참여이력' not in df_current.columns:
                df_current['참여이력'] = '신규' # 컬럼이 없으면 전원 신규로 간주
            else:
                df_current['참여이력'] = df_current['참여이력'].astype(str).apply(lambda x: '크루' if '크루' in x or '기존' in x else '신규')

            # 고유 식별 키 생성 (이름+학교+성별) -> 과거 명단과 대조용
            df_current['매칭키'] = df_current['이름'] + "_" + df_current['소속학교'] + "_" + df_current['성별']
            
            # 과거 대기자 명단 처리
            past_keys = set()
            if past_waitlist_file is not None:
                if past_waitlist_file.name.endswith('.csv'):
                    df_past = pd.read_csv(past_waitlist_file)
                else:
                    df_past = pd.read_excel(past_waitlist_file)
                
                # 과거 파일도 동일하게 키 생성 시도
                try:
                    df_past['성별'] = df_past['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
                    df_past['소속학교'] = df_past['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
                    df_past['매칭키'] = df_past['이름'] + "_" + df_past['소속학교'] + "_" + df_past['성별']
                    past_keys = set(df_past['매칭키'].tolist())
                    st.success(f"✅ 저번 파티 대기자 {len(past_keys)}명의 데이터를 성공적으로 불러왔습니다.")
                except Exception as e:
                    st.warning("⚠️ 저번 파티 대기자 파일의 형식이 맞지 않아(이름, 성별, 소속학교 누락) 우선순위 배정을 생략합니다.")

            # ==========================================
            # [핵심] 선발 알고리즘 실행 버튼
            # ==========================================
            if st.button("🚀 자동 선발 알고리즘 실행!", use_container_width=True):
                with st.spinner("최적의 참가자 및 대기자를 선발하고 있습니다..."):
                    
                    df_current['우선순위'] = df_current['매칭키'].apply(lambda x: True if x in past_keys else False)
                    
                    # 남녀 그룹 분리
                    df_m = df_current[df_current['성별'] == '남'].copy()
                    df_w = df_current[df_current['성별'] == '여'].copy()
                    
                    total_m_applied = len(df_m)
                    total_w_applied = len(df_w)
                    
                    # 1. 목표 정원 계산 (유연한 보정 알고리즘)
                    base_target = total_capacity // 2
                    
                    target_m = base_target
                    target_w = base_target
                    
                    if total_w_applied < base_target:
                        target_w = total_w_applied
                        target_m = total_capacity - target_w # 남은 자리를 남자에게
                    elif total_m_applied < base_target:
                        target_m = total_m_applied
                        target_w = total_capacity - target_m # 남은 자리를 여자에게
                        
                    # 만약 지원자 수가 목표 정원보다도 적다면? (예: 100명 정원인데 총 80명 지원)
                    target_m = min(target_m, total_m_applied)
                    target_w = min(target_w, total_w_applied)

                    def select_participants(df_pool, target_count):
                        # 1순위: 과거 대기자 무조건 선발
                        df_priority = df_pool[df_pool['우선순위'] == True]
                        df_normal = df_pool[df_pool['우선순위'] == False]
                        
                        selected_priority = df_priority.sample(n=min(len(df_priority), target_count), random_state=random.randint(1,10000))
                        remaining_target = target_count - len(selected_priority)
                        
                        if remaining_target <= 0:
                            return selected_priority, df_pool.drop(selected_priority.index)
                            
                        # 2순위: 남은 자리를 신규 50%, 크루 50% 분배
                        df_new = df_normal[df_normal['참여이력'] == '신규']
                        df_crew = df_normal[df_normal['참여이력'] == '크루']
                        
                        target_new = remaining_target // 2 + remaining_target % 2 # 홀수면 신규에게 1자리 양보
                        target_crew = remaining_target // 2
                        
                        # [Spill-over 로직] 한쪽 그룹이 부족하면 남은 자리를 다른 그룹으로 넘김
                        if len(df_new) < target_new:
                            shortfall = target_new - len(df_new)
                            target_crew += shortfall
                            target_new = len(df_new)
                        elif len(df_crew) < target_crew:
                            shortfall = target_crew - len(df_crew)
                            target_new += shortfall
                            target_crew = len(df_crew)
                            
                        target_new = min(target_new, len(df_new))
                        target_crew = min(target_crew, len(df_crew))
                        
                        selected_new = df_new.sample(n=target_new, random_state=random.randint(1,10000))
                        selected_crew = df_crew.sample(n=target_crew, random_state=random.randint(1,10000))
                        
                        final_selected = pd.concat([selected_priority, selected_new, selected_crew])
                        final_waitlisted = df_pool.drop(final_selected.index)
                        
                        return final_selected, final_waitlisted

                    # 남/여 각각 선발 알고리즘 가동
                    selected_m, waitlist_m = select_participants(df_m, target_m)
                    selected_w, waitlist_w = select_participants(df_w, target_w)
                    
                    # 최종 합치기
                    final_selected_df = pd.concat([selected_m, selected_w]).sample(frac=1).reset_index(drop=True)
                    final_waitlist_df = pd.concat([waitlist_m, waitlist_w]).sample(frac=1).reset_index(drop=True)
                    
                    # Session State에 저장 (Step 2에서 사용하기 위함)
                    st.session_state['selected_participants'] = final_selected_df
                    
                    st.success("🎉 참가자 선발이 완료되었습니다!")
                    
                    # 결과 대시보드 출력
                    st.subheader("📊 선발 결과 요약")
                    col_s1, col_s2, col_s3 = st.columns(3)
                    col_s1.metric("총 신청자", f"{len(df_current)}명")
                    col_s2.metric("최종 선발자 (정원)", f"{len(final_selected_df)}명")
                    col_s3.metric("대기자 (미선정자)", f"{len(final_waitlist_df)}명")
                    
                    st.info(f"**선발 성비:** 👨 남성 {len(selected_m)}명 / 👩‍🦰 여성 {len(selected_w)}명")
                    
                    # 데이터프레임 표시 및 엑셀 다운로드 로직
                    st.write("### ✅ 최종 참가 확정 명단")
                    st.dataframe(final_selected_df.drop(columns=['매칭키', '우선순위']), use_container_width=True)
                    
                    st.write("### ⏳ 대기자 명단 (다음 파티 최우선권 부여)")
                    st.dataframe(final_waitlist_df.drop(columns=['매칭키', '우선순위']), use_container_width=True)
                    
                    # 엑셀 다운로드 버튼 생성 함수
                    def to_excel(df):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.drop(columns=['매칭키', '우선순위']).to_excel(writer, index=False, sheet_name='Sheet1')
                        processed_data = output.getvalue()
                        return processed_data

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        st.download_button(label="📥 최종 참가자 명단 엑셀 다운로드",
                                           data=to_excel(final_selected_df),
                                           file_name='파티_최종참가자명단.xlsx',
                                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    with col_btn2:
                        st.download_button(label="📥 대기자 명단 엑셀 다운로드",
                                           data=to_excel(final_waitlist_df),
                                           file_name='파티_대기자명단.xlsx',
                                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

with tab2:
    st.info("Step 1에서 확정된 참가자 명단을 바탕으로 2, 3, 4, 5번 기획(초정밀 자리배치)이 구동될 공간입니다.")

with tab3:
    st.info("Step 2의 배치가 끝나면, 6, 7, 8번 기획(검증 리포트 및 통계)이 출력될 공간입니다.")
