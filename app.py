import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

st.title("🍻 청취담 연합파티 스케줄러 (사전 배치용)")
st.subheader("교통대 x 건국대 글로컬 캠퍼스")

# --- 1. 사이드바 설정 ---
st.sidebar.header("⚙️ 파티 설정")
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)

# --- 2. 전체 스케줄 생성 알고리즘 ---
def generate_full_schedule(people_list, num_tables, total_rounds=3):
    n = len(people_list)
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    # --- 전체 인원 통계 정밀 계산 ---
    total_m = sum(1 for p in people_list if p['성별'] == '남')
    total_w = sum(1 for p in people_list if p['성별'] == '여')
    total_sch_a = sum(1 for p in people_list if p['소속학교'] == '교통대')
    total_sch_b = sum(1 for p in people_list if p['소속학교'] == '건국대')
    
    ratio_m = total_m / n
    ratio_sch_a = total_sch_a / n

    best_all_rounds = []
    global_min_penalty = float('inf')

    # 복잡한 조건 처리를 위해 시도 횟수 50번 유지
    for attempt in range(50): 
        met_pairs = set()
        # [수정] 이름이 아닌 '고유ID'를 기준으로 방문 테이블 기록
        person_visited_tables = {p['고유ID']: set() for p in people_list}
        current_all_rounds = []
        total_penalty = 0

        for r in range(total_rounds):
            unseated = people_list.copy()
            random.shuffle(unseated)
            round_tables = [[] for _ in range(num_tables)]

            for t_idx, t_size in enumerate(table_sizes):
                for _ in range(t_size):
                    if not unseated: break

                    best_person = None
                    min_p = float('inf')

                    for p in unseated:
                        p_penalty = 0
                        
                        # 1순위: 중복 만남 원천 차단 (절대 조건) - [수정] 동명이인 방지를 위해 고유ID 비교
                        for seated in round_tables[t_idx]:
                            pair = tuple(sorted([p['고유ID'], seated['고유ID']]))
                            if pair in met_pairs:
                                p_penalty += 10000 
                                
                        # 1.5순위: 지박령 방지 - [수정] 고유ID 기준
                        if t_idx in person_visited_tables[p['고유ID']]:
                            p_penalty += 8000

                        # 임시 착석 후 테이블 상태 확인
                        temp_table = round_tables[t_idx] + [p]
                        size = len(temp_table)
                        m_count = sum(1 for x in temp_table if x['성별'] == '남')
                        w_count = sum(1 for x in temp_table if x['성별'] == '여')
                        sch_a_count = sum(1 for x in temp_table if x['소속학교'] == '교통대')
                        sch_b_count = sum(1 for x in temp_table if x['소속학교'] == '건국대')

                        # =========================================================
                        # 2순위: 최소 1명 보장 및 소수 인원 쏠림 방지 
                        # =========================================================
                        if size == t_size:
                            
                            # [성별 조건 검사]
                            if total_w >= num_tables and w_count == 0:
                                p_penalty += 3000 
                            elif total_w < num_tables and w_count > 1:
                                p_penalty += 3000 
                                
                            if total_m >= num_tables and m_count == 0:
                                p_penalty += 3000
                            elif total_m < num_tables and m_count > 1:
                                p_penalty += 3000

                            # [학교 조건 검사]
                            if total_sch_b >= num_tables and sch_b_count == 0:
                                p_penalty += 3000 
                            elif total_sch_b < num_tables and sch_b_count > 1:
                                p_penalty += 3000 
                                
                            if total_sch_a >= num_tables and sch_a_count == 0:
                                p_penalty += 3000
                            elif total_sch_a < num_tables and sch_a_count > 1:
                                p_penalty += 3000

                        # 3순위: 진행 중 동적 비율 유지 (자리를 채우는 과정에서 자연스러운 분배 유도)
                        target_m = size * ratio_m
                        target_sch_a = size * ratio_sch_a
                        p_penalty += abs(m_count - target_m) * 15
                        p_penalty += abs(sch_a_count - target_sch_a) * 15

                        if p_penalty < min_p:
                            min_p = p_penalty
                            best_person = p

                    # 최적 인원 착석 및 방문 기록
                    round_tables[t_idx].append(best_person)
                    unseated.remove(best_person)
                    total_penalty += min_p
                    person_visited_tables[best_person['고유ID']].add(t_idx) 

            current_all_rounds.append(round_tables)

            for table in round_tables:
                for i in range(len(table)):
                    for j in range(i + 1, len(table)):
                        pair = tuple(sorted([table[i]['고유ID'], table[j]['고유ID']]))
                        met_pairs.add(pair)

        if total_penalty < global_min_penalty:
            global_min_penalty = total_penalty
            best_all_rounds = current_all_rounds

        if global_min_penalty == 0:
            break

    return best_all_rounds

# --- 3. 메인 화면 ---
st.write("---")
st.write("### 📂 참가자 명단 업로드")
st.info("파티 개최 전, 확정된 전체 인원 명단을 올려주세요. (.xlsx 또는 .csv 파일 모두 지원)")
# [수정] csv 파일도 업로드 가능하도록 type 추가
uploaded_file = st.file_uploader("엑셀/CSV 파일 선택", type=['xlsx', 'csv'])

if uploaded_file is not None:
    # [수정] 파일 확장자에 따라 다르게 읽어오기
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    if not {'이름', '성별', '소속학교'}.issubset(df.columns):
        st.error("⚠️ 파일 첫 줄에 '이름', '성별', '소속학교' 가 정확히 적혀있는지 확인해주세요!")
    else:
        # ==========================================
        # [신규 핵심 기능] 텍스트 자동 정제 및 동명이인 처리
        # ==========================================
        # 1. 성별 텍스트 통일 ('남성' -> '남', '여성' -> '여')
        df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
        
        # 2. 학교 텍스트 통일 ('한국교통대~' -> '교통대', '건국대~' -> '건국대')
        df['소속학교'] = df['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
        
        people_list = df.to_dict('records')
        
        # 3. 동명이인 구분을 위한 내부 '고유ID' 발급
        for idx, p in enumerate(people_list):
            p['고유ID'] = f"{p['이름']}_{idx}"

        st.write(f"✅ **총 참가자 수: {len(df)}명**")
        
        st.write("---")
        if st.button("🚀 전체 라운드(1~3) 자리 배치 스케줄 생성!"):
            with st.spinner('실제 현장 데이터를 분석하여 최적의 동선을 계산 중입니다...'):
                
                # 전체 스케줄 생성 함수 실행
                all_rounds_data = generate_full_schedule(people_list, table_count)
                
                st.success("🎉 파티 전체 스케줄 배치가 완료되었습니다!")
                
                # ==========================================
                # 운영진 확인용: 라운드별 테이블 배치도
                # ==========================================
                st.write("### 🗺️ 라운드별 테이블 배치도 (운영진용)")
                st.info("아래 각 라운드 탭을 클릭하여 테이블별 착석 인원(이름, 성별, 학교)을 확인하세요.")
                
                tabs = st.tabs([f"{r + 1}라운드" for r in range(len(all_rounds_data))])
                
                for r_idx, tab in enumerate(tabs):
                    with tab:
                        round_tables = all_rounds_data[r_idx]
                        cols = st.columns(3)
                        for t_idx, table in enumerate(round_tables):
                            col = cols[t_idx % 3]
                            with col:
                                st.markdown(f"**📍 {t_idx + 1}번 테이블**")
                                if table:
                                    table_df = pd.DataFrame(table)[['이름', '성별', '소속학교']]
                                    st.dataframe(table_df, hide_index=True, use_container_width=True)
                                else:
                                    st.write("빈 테이블")
                                st.write("") 
                
                st.write("---")
                
                # ==========================================
                # 참가자 배포용: 개인별 파티 스케줄
                # ==========================================
                schedule_results = []
                for idx, person in enumerate(people_list):
                    name = person['이름']
                    uid = person['고유ID'] # 동명이인 추적을 위해 고유ID 사용
                    row_data = {
                        "번호": idx + 1,
                        "이름": name, # 화면에는 원래 이름만 예쁘게 출력
                        "성별": person['성별'],
                        "소속학교": person['소속학교']
                    }
                    
                    for r_idx, round_tables in enumerate(all_rounds_data):
                        for t_idx, table in enumerate(round_tables):
                            if any(p['고유ID'] == uid for p in table):
                                row_data[f"{r_idx + 1}라운드 테이블"] = f"{t_idx + 1}번"
                                break
                    
                    schedule_results.append(row_data)
                
                result_df = pd.DataFrame(schedule_results)
                
                st.write("### 📋 개인별 파티 스케줄표 (전체 명단)")
                st.dataframe(result_df, hide_index=True, use_container_width=True)
                
                st.write("---")
                st.write("### 📝 개별 안내용 텍스트 (복사해서 카톡 전송용)")
                
                text_output = ""
                for index, row in result_df.iterrows():
                    text_output += f"{row['번호']}. {row['이름']}\n"
                    text_output += f"- 첫번째 테이블: {row['1라운드 테이블']}\n"
                    text_output += f"- 두번째 테이블: {row['2라운드 테이블']}\n"
                    text_output += f"- 세번째 테이블: {row['3라운드 테이블']}\n\n"
                
                st.text_area("아래 내용을 전체 복사하세요.", text_output, height=300)
