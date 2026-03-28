import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

st.title("🍻 청취담 연합파티 스케줄러 (사전 배치용)")
st.subheader("교통대 x 건국대 글로컬 캠퍼스")

# --- 1. 사이드바 설정 ---
st.sidebar.header("⚙️ 파티 설정")
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)
# 라운드 선택 버튼은 삭제됨! (항상 1~3라운드 전체를 한 번에 생성함)

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
        person_visited_tables = {p['이름']: set() for p in people_list}
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
                        
                        # 1순위: 중복 만남 원천 차단 (절대 조건)
                        for seated in round_tables[t_idx]:
                            pair = tuple(sorted([p['이름'], seated['이름']]))
                            if pair in met_pairs:
                                p_penalty += 10000 
                                
                        # 1.5순위: 지박령 방지
                        if t_idx in person_visited_tables[p['이름']]:
                            p_penalty += 8000

                        # 임시 착석 후 테이블 상태 확인
                        temp_table = round_tables[t_idx] + [p]
                        size = len(temp_table)
                        m_count = sum(1 for x in temp_table if x['성별'] == '남')
                        w_count = sum(1 for x in temp_table if x['성별'] == '여')
                        sch_a_count = sum(1 for x in temp_table if x['소속학교'] == '교통대')
                        sch_b_count = sum(1 for x in temp_table if x['소속학교'] == '건국대')

                        # =========================================================
                        # [신규 추가] 2순위: 최소 1명 보장 및 소수 인원 쏠림 방지 
                        # =========================================================
                        # 테이블의 마지막 자리가 채워지는 시점에 조건을 엄격히 검사
                        if size == t_size:
                            
                            # [성별 조건 검사]
                            if total_w >= num_tables and w_count == 0:
                                p_penalty += 3000 # 여자가 충분한데 테이블에 0명이면 강력 패널티 (최소 1명 보장)
                            elif total_w < num_tables and w_count > 1:
                                p_penalty += 3000 # 여자가 부족한데 한 테이블에 2명 이상 몰리면 패널티 (분산 유도, 남자 넷 테이블 자연 허용)
                                
                            if total_m >= num_tables and m_count == 0:
                                p_penalty += 3000
                            elif total_m < num_tables and m_count > 1:
                                p_penalty += 3000

                            # [학교 조건 검사]
                            if total_sch_b >= num_tables and sch_b_count == 0:
                                p_penalty += 3000 # 건국대가 충분한데 0명이면 강력 패널티 (최소 1명 보장)
                            elif total_sch_b < num_tables and sch_b_count > 1:
                                p_penalty += 3000 # 건국대가 부족한데 몰리면 패널티 (교통대 넷 테이블 자연 허용)
                                
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
                    person_visited_tables[best_person['이름']].add(t_idx) 

            current_all_rounds.append(round_tables)

            for table in round_tables:
                for i in range(len(table)):
                    for j in range(i + 1, len(table)):
                        pair = tuple(sorted([table[i]['이름'], table[j]['이름']]))
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
st.info("파티 개최 전, 확정된 전체 인원 명단을 올려주세요.")
uploaded_file = st.file_uploader("엑셀 파일 선택", type=['xlsx'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    if not {'이름', '성별', '소속학교'}.issubset(df.columns):
        st.error("⚠️ 엑셀 파일 첫 줄에 '이름', '성별', '소속학교' 가 정확히 적혀있는지 확인해주세요!")
    else:
        st.write(f"✅ **총 참가자 수: {len(df)}명**")
        
        st.write("---")
        if st.button("🚀 전체 라운드(1~3) 자리 배치 스케줄 생성!"):
            with st.spinner('3시간 동안 절대 겹치지 않는 최적의 동선을 계산 중입니다...'):
                people_list = df.to_dict('records')
                
                # 전체 스케줄 생성 함수 실행
                all_rounds_data = generate_full_schedule(people_list, table_count)
                
                st.success("🎉 파티 전체 스케줄 배치가 완료되었습니다!")
                
                # ==========================================
                # [신규 기능] 1. 운영진 확인용: 라운드별 테이블 배치도
                # ==========================================
                st.write("### 🗺️ 라운드별 테이블 배치도 (운영진용)")
                st.info("아래 각 라운드 탭을 클릭하여 테이블별 착석 인원(이름, 성별, 학교)을 확인하세요.")
                
                # Streamlit의 탭 기능을 사용하여 1, 2, 3라운드를 분리
                tabs = st.tabs([f"{r + 1}라운드" for r in range(len(all_rounds_data))])
                
                for r_idx, tab in enumerate(tabs):
                    with tab:
                        round_tables = all_rounds_data[r_idx]
                        # 화면을 3단으로 나누어 표를 보기 좋게 정렬
                        cols = st.columns(3)
                        for t_idx, table in enumerate(round_tables):
                            col = cols[t_idx % 3]
                            with col:
                                st.markdown(f"**📍 {t_idx + 1}번 테이블**")
                                if table:
                                    # 이름, 성별, 소속학교만 추출하여 표로 구성
                                    table_df = pd.DataFrame(table)[['이름', '성별', '소속학교']]
                                    # 인덱스(0,1,2..) 번호를 숨겨서 더 깔끔하게 출력
                                    st.dataframe(table_df, hide_index=True, use_container_width=True)
                                else:
                                    st.write("빈 테이블")
                                st.write("") # 간격 띄우기
                
                st.write("---")
                
                # ==========================================
                # 2. 참가자 배포용: 개인별 파티 스케줄
                # ==========================================
                schedule_results = []
                for idx, person in enumerate(people_list):
                    name = person['이름']
                    row_data = {
                        "번호": idx + 1,
                        "이름": name,
                        "성별": person['성별'],
                        "소속학교": person['소속학교']
                    }
                    
                    for r_idx, round_tables in enumerate(all_rounds_data):
                        for t_idx, table in enumerate(round_tables):
                            if any(p['이름'] == name for p in table):
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
