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

    # [핵심 로직] 각 테이블이 가져야 할 수학적 최소/최대 인원 사전 계산
    min_w = total_w // num_tables
    max_w = (total_w + num_tables - 1) // num_tables if num_tables else 0
    min_m = total_m // num_tables
    max_m = (total_m + num_tables - 1) // num_tables if num_tables else 0
    
    min_sch_b = total_sch_b // num_tables
    max_sch_b = (total_sch_b + num_tables - 1) // num_tables if num_tables else 0
    min_sch_a = total_sch_a // num_tables
    max_sch_a = (total_sch_a + num_tables - 1) // num_tables if num_tables else 0

    best_all_rounds = []
    global_min_penalty = float('inf')

    # 복잡한 조건 처리를 위해 시도 횟수 50번 유지
    for attempt in range(50): 
        met_pairs = set()
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
                        
                        # 1순위: 중복 만남 원천 차단
                        for seated in round_tables[t_idx]:
                            pair = tuple(sorted([p['고유ID'], seated['고유ID']]))
                            if pair in met_pairs:
                                p_penalty += 10000 
                                
                        # 1.5순위: 지박령(고정석) 방지
                        if t_idx in person_visited_tables[p['고유ID']]:
                            p_penalty += 8000

                        # [유연한 로직] 학과 정보가 존재하고 미기재가 아닐 때만 지인 차단 발동
                        for seated in round_tables[t_idx]:
                            if p.get('학과') and seated.get('학과'):
                                if p['학과'] != '미기재' and p['소속학교'] == seated['소속학교'] and p['학과'] == seated['학과']:
                                    p_penalty += 20000

                        # 현재 테이블에 이 사람을 앉혔을 때의 가상 데이터
                        temp_w = sum(1 for x in round_tables[t_idx] if x['성별'] == '여') + (1 if p['성별'] == '여' else 0)
                        temp_m = sum(1 for x in round_tables[t_idx] if x['성별'] == '남') + (1 if p['성별'] == '남' else 0)
                        temp_sch_b = sum(1 for x in round_tables[t_idx] if x['소속학교'] == '건국대') + (1 if p['소속학교'] == '건국대' else 0)
                        temp_sch_a = sum(1 for x in round_tables[t_idx] if x['소속학교'] == '교통대') + (1 if p['소속학교'] == '교통대' else 0)

                        # 2순위: 최대 정원 통제 및 수학적 고갈 방지
                        if temp_w > max_w: p_penalty += 50000
                        if temp_m > max_m: p_penalty += 50000
                        if temp_sch_b > max_sch_b: p_penalty += 50000
                        if temp_sch_a > max_sch_a: p_penalty += 50000

                        if p['성별'] == '여':
                            unseated_w = sum(1 for x in unseated if x['성별'] == '여')
                            tables_needing_w = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '여') < min_w)
                            if (temp_w - 1) >= min_w and unseated_w <= tables_needing_w:
                                p_penalty += 50000
                                
                        elif p['성별'] == '남':
                            unseated_m = sum(1 for x in unseated if x['성별'] == '남')
                            tables_needing_m = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '남') < min_m)
                            if (temp_m - 1) >= min_m and unseated_m <= tables_needing_m:
                                p_penalty += 50000

                        if p['소속학교'] == '건국대':
                            unseated_sch_b = sum(1 for x in unseated if x['소속학교'] == '건국대')
                            tables_needing_sch_b = sum(1 for t in round_tables if sum(1 for x in t if x['소속학교'] == '건국대') < min_sch_b)
                            if (temp_sch_b - 1) >= min_sch_b and unseated_sch_b <= tables_needing_sch_b:
                                p_penalty += 50000
                                
                        elif p['소속학교'] == '교통대':
                            unseated_sch_a = sum(1 for x in unseated if x['소속학교'] == '교통대')
                            tables_needing_sch_a = sum(1 for t in round_tables if sum(1 for x in t if x['소속학교'] == '교통대') < min_sch_a)
                            if (temp_sch_a - 1) >= min_sch_a and unseated_sch_a <= tables_needing_sch_a:
                                p_penalty += 50000

                        if p_penalty < min_p:
                            min_p = p_penalty
                            best_person = p

                    if best_person is not None:
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

uploaded_file = st.file_uploader("엑셀/CSV 파일 선택", type=['xlsx', 'csv'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    # ==========================================
    # [추가된 로직] 컬럼명 유연한 인식 ('학과', '학년' 포함 여부)
    # ==========================================
    # '학과'라는 단어가 포함된 첫 번째 컬럼 찾기
    dept_col = next((col for col in df.columns if '학과' in col), None)
    # '학년'이라는 단어가 포함된 첫 번째 컬럼 찾기
    grade_col = next((col for col in df.columns if '학년' in col), None)

    rename_dict = {}
    if dept_col and dept_col != '학과':
        rename_dict[dept_col] = '학과'
    if grade_col and grade_col != '학년':
        rename_dict[grade_col] = '학년'
        
    # 찾은 컬럼들의 이름을 각각 '학과', '학년'으로 통일
    if rename_dict:
        df = df.rename(columns=rename_dict)
    # ==========================================

    # 엑셀 파일 검증 시 이름, 성별, 소속학교만 필수
    if not {'이름', '성별', '소속학교'}.issubset(df.columns):
        st.error("⚠️ 파일 첫 줄에 최소한 '이름', '성별', '소속학교' 가 정확히 적혀있는지 확인해주세요!")
    else:
        # 데이터 자동 정제
        df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
        df['소속학교'] = df['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
        
        # ==========================================
        # [데이터 전처리] 학과 및 학년 컬럼 동적 처리 (위에서 이름이 정규화되었으므로 그대로 사용)
        # ==========================================
        has_dept = '학과' in df.columns
        if has_dept:
            df['학과'] = df['학과'].fillna('미기재')
        else:
            df['학과'] = '미기재'
            
        has_grade = '학년' in df.columns
        if has_grade:
            df['학년'] = df['학년'].astype(str).replace('nan', '미기재')
        else:
            df['학년'] = '미기재'
        
        # ==========================================
        # [신규 기능] 대시보드 통계 계산 및 UI 출력
        # ==========================================
        total_count = len(df)
        
        # 1. 성별 통계
        total_m_count = len(df[df['성별'] == '남'])
        total_w_count = len(df[df['성별'] == '여'])
        ratio_m = (total_m_count / total_count) * 100 if total_count > 0 else 0
        ratio_w = (total_w_count / total_count) * 100 if total_count > 0 else 0
        
        # 2. 소속학교 통계
        total_sch_a_count = len(df[df['소속학교'] == '교통대'])
        total_sch_b_count = len(df[df['소속학교'] == '건국대'])
        ratio_sch_a = (total_sch_a_count / total_count) * 100 if total_count > 0 else 0
        ratio_sch_b = (total_sch_b_count / total_count) * 100 if total_count > 0 else 0
        
        st.write(f"✅ **총 참가자 수: {total_count}명**")
        st.info(f"📊 **참가자 성비:** 👨 남성 {total_m_count}명 ({ratio_m:.1f}%) / 👩‍🦰 여성 {total_w_count}명 ({ratio_w:.1f}%)")
        st.info(f"🏫 **소속학교 비율:** 🚆 교통대 {total_sch_a_count}명 ({ratio_sch_a:.1f}%) / 🐂 건국대 {total_sch_b_count}명 ({ratio_sch_b:.1f}%)")
        
        # 3. 학년 통계 (데이터가 존재하는 경우에만 출력)
        if has_grade:
            grade_counts = df[df['학년'] != '미기재']['학년'].value_counts().sort_index()
            if not grade_counts.empty:
                grade_stats_str = " / ".join([f"{grade} {count}명 ({(count/total_count)*100:.1f}%)" for grade, count in grade_counts.items()])
                st.info(f"🎓 **학년별 비율:** {grade_stats_str}")
        
        people_list = df.to_dict('records')
        
        # 동명이인 처리를 위한 고유 ID 발급
        for idx, p in enumerate(people_list):
            p['고유ID'] = f"{p['이름']}_{idx}"
        
        st.write("---")
        if st.button("🚀 전체 라운드(1~3) 자리 배치 스케줄 생성!"):
            with st.spinner('실제 현장 데이터를 분석하여 최적의 동선을 계산 중입니다...'):
                
                all_rounds_data = generate_full_schedule(people_list, table_count)
                
                st.success("🎉 파티 전체 스케줄 배치가 완료되었습니다!")
                
                st.write("### 🗺️ 라운드별 테이블 배치도 (운영진용)")
                st.info("아래 각 라운드 탭을 클릭하여 테이블별 착석 인원 정보를 확인하세요.")
                
                tabs = st.tabs([f"{r + 1}라운드" for r in range(len(all_rounds_data))])
                
                # 출력할 컬럼 동적 설정 (학과/학년이 없으면 화면에서 숨김)
                display_cols = ['이름', '성별', '소속학교']
                if has_dept: display_cols.append('학과')
                if has_grade: display_cols.append('학년')

                for r_idx, tab in enumerate(tabs):
                    with tab:
                        round_tables = all_rounds_data[r_idx]
                        cols = st.columns(3)
                        for t_idx, table in enumerate(round_tables):
                            col = cols[t_idx % 3]
                            with col:
                                st.markdown(f"**📍 {t_idx + 1}번 테이블**")
                                if table:
                                    table_df = pd.DataFrame(table)[display_cols]
                                    st.dataframe(table_df, hide_index=True, use_container_width=True)
                                else:
                                    st.write("빈 테이블")
                                st.write("") 
                
                st.write("---")
                
                schedule_results = []
                for idx, person in enumerate(people_list):
                    name = person['이름']
                    uid = person['고유ID']
                    row_data = {
                        "번호": idx + 1,
                        "이름": name, 
                        "성별": person['성별'],
                        "소속학교": person['소속학교']
                    }
                    if has_dept:
                        row_data["학과"] = person['학과']
                    if has_grade:
                        row_data["학년"] = person['학년']
                    
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
