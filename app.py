import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

# ==========================================
# [보안] 관리자 로그인 시스템 (기존 유지)
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

st.title("🍻 청취담 연합파티 스케줄러 (사전 배치용)")
st.subheader("교통대 x 건국대 글로컬 캠퍼스")

# --- 1. 사이드바 설정 ---
st.sidebar.header("⚙️ 파티 설정")
party_capacity = st.sidebar.number_input("이번 파티 참가 정원 (명)", min_value=4, value=48, step=4)
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)

# --- 2. 전체 스케줄 생성 알고리즘 (기존 무결점 로직 유지) ---
def generate_full_schedule(people_list, num_tables, total_rounds=3):
    n = len(people_list)
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    total_m = sum(1 for p in people_list if p['성별'] == '남')
    total_w = sum(1 for p in people_list if p['성별'] == '여')
    total_sch_a = sum(1 for p in people_list if p['소속학교'] == '교통대')
    total_sch_b = sum(1 for p in people_list if p['소속학교'] == '건국대')

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
                        for seated in round_tables[t_idx]:
                            pair = tuple(sorted([p['고유ID'], seated['고유ID']]))
                            if pair in met_pairs: p_penalty += 10000 
                        if t_idx in person_visited_tables[p['고유ID']]: p_penalty += 8000
                        for seated in round_tables[t_idx]:
                            if p.get('학과') and seated.get('학과'):
                                if p['학과'] != '미기재' and p['소속학교'] == seated['소속학교'] and p['학과'] == seated['학과']:
                                    p_penalty += 20000
                        temp_w = sum(1 for x in round_tables[t_idx] if x['성별'] == '여') + (1 if p['성별'] == '여' else 0)
                        temp_m = sum(1 for x in round_tables[t_idx] if x['성별'] == '남') + (1 if p['성별'] == '남' else 0)
                        temp_sch_b = sum(1 for x in round_tables[t_idx] if x['소속학교'] == '건국대') + (1 if p['소속학교'] == '건국대' else 0)
                        temp_sch_a = sum(1 for x in round_tables[t_idx] if x['소속학교'] == '교통대') + (1 if p['소속학교'] == '교통대' else 0)
                        if temp_w > max_w: p_penalty += 50000
                        if temp_m > max_m: p_penalty += 50000
                        if temp_sch_b > max_sch_b: p_penalty += 50000
                        if temp_sch_a > max_sch_a: p_penalty += 50000
                        if p['성별'] == '여':
                            unseated_w = sum(1 for x in unseated if x['성별'] == '여')
                            tables_needing_w = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '여') < min_w)
                            if (temp_w - 1) >= min_w and unseated_w <= tables_needing_w: p_penalty += 50000
                        elif p['성별'] == '남':
                            unseated_m = sum(1 for x in unseated if x['성별'] == '남')
                            tables_needing_m = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '남') < min_m)
                            if (temp_m - 1) >= min_m and unseated_m <= tables_needing_m: p_penalty += 50000
                        if p['소속학교'] == '건국대':
                            unseated_sch_b = sum(1 for x in unseated if x['소속학교'] == '건국대')
                            tables_needing_sch_b = sum(1 for t in round_tables if sum(1 for x in t if x['소속학교'] == '건국대') < min_sch_b)
                            if (temp_sch_b - 1) >= min_sch_b and unseated_sch_b <= tables_needing_sch_b: p_penalty += 50000
                        elif p['소속학교'] == '교통대':
                            unseated_sch_a = sum(1 for x in unseated if x['소속학교'] == '교통대')
                            tables_needing_sch_a = sum(1 for t in round_tables if sum(1 for x in t if x['소속학교'] == '교통대') < min_sch_a)
                            if (temp_sch_a - 1) >= min_sch_a and unseated_sch_a <= tables_needing_sch_a: p_penalty += 50000
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
        if global_min_penalty == 0: break
    return best_all_rounds

# --- 3. 메인 화면 ---
st.write("---")
st.write("### 📂 파티 명단 업로드")
col_u1, col_u2 = st.columns(2)
with col_u1:
    uploaded_file = st.file_uploader("📂 [필수] 이번 파티 전체 신청자 (엑셀/CSV)", type=['xlsx', 'csv'])
with col_u2:
    past_waitlist_file = st.file_uploader("📂 [선택] 저번 파티 미선정자 명단", type=['xlsx', 'csv'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
    else: df = pd.read_excel(uploaded_file)
        
    # 컬럼명 유연한 인식
    target_keywords = ['이름', '성별', '소속학교', '학과', '학년', '참여이력', '신규']
    rename_dict = {}
    for keyword in target_keywords:
        matched_col = next((col for col in df.columns if keyword in str(col)), None)
        if matched_col and matched_col != keyword:
            if keyword == '신규': rename_dict[matched_col] = '참여이력'
            else: rename_dict[matched_col] = keyword
    if rename_dict: df = df.rename(columns=rename_dict)

    if not {'이름', '성별', '소속학교'}.issubset(df.columns):
        st.error("⚠️ 파일 첫 줄에 최소한 '이름', '성별', '소속학교' 관련 단어가 포함되어 있는지 확인해주세요!")
    else:
        # 데이터 정제 및 기본 컬럼 보장
        df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
        df['소속학교'] = df['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
        df['학과'] = df['학과'].fillna('미기재') if '학과' in df.columns else '미기재'
        df['학년'] = df['학년'].astype(str).replace('nan', '미기재') if '학년' in df.columns else '미기재'
        if '참여이력' not in df.columns: df['참여이력'] = '신규' 
        else: df['참여이력'] = df['참여이력'].astype(str).apply(lambda x: '크루' if '크루' in x or '기존' in x else '신규')

        # ==========================================
        # [기존 로직 유지] 대시보드 통계 즉시 출력
        # ==========================================
        total_count = len(df)
        total_m_count = len(df[df['성별'] == '남'])
        total_w_count = len(df[df['성별'] == '여'])
        total_sch_a_count = len(df[df['소속학교'] == '교통대'])
        total_sch_b_count = len(df[df['소속학교'] == '건국대'])
        
        st.write(f"✅ **총 신청 인원: {total_count}명**")
        st.info(f"📊 **참가자 성비:** 👨 남성 {total_m_count}명 / 👩‍🦰 여성 {total_w_count}명")
        st.info(f"🏫 **소속학교 비율:** 🚆 교통대 {total_sch_a_count}명 / 🐂 건국대 {total_sch_b_count}명")
        if '학년' in df.columns:
            grade_counts = df[df['학년'] != '미기재']['학년'].value_counts().sort_index()
            if not grade_counts.empty:
                grade_stats_str = " / ".join([f"{grade} {count}명" for grade, count in grade_counts.items()])
                st.info(f"🎓 **학년별 비율:** {grade_stats_str}")

        # 과거 대기자 키 생성
        past_keys = set()
        if past_waitlist_file:
            try:
                df_past = pd.read_csv(past_waitlist_file) if past_waitlist_file.name.endswith('.csv') else pd.read_excel(past_waitlist_file)
                df_past['매칭키'] = df_past['이름'].astype(str) + df_past['성별'].astype(str) + df_past['소속학교'].astype(str)
                past_keys = set(df_past['매칭키'].tolist())
                st.success(f"✅ 저번 대기자 {len(past_keys)}명을 우선 선발 리스트에 추가했습니다.")
            except: st.warning("⚠️ 대기자 파일 형식이 맞지 않습니다.")

        # ==========================================
        # [추가 기능] 1단계: 참가자 랜덤 선발
        # ==========================================
        st.write("---")
        if st.button("🚀 1단계: 참가 정원에 맞춰 참가자/대기자 랜덤 선발", use_container_width=True):
            df['매칭키'] = df['이름'].astype(str) + df['성별'].astype(str) + df['소속학교'].astype(str)
            df['우선순위'] = df['매칭키'].apply(lambda x: True if x in past_keys else False)
            
            df_m = df[df['성별'] == '남'].copy()
            df_w = df[df['성별'] == '여'].copy()
            
            target_m, target_w = party_capacity // 2, party_capacity // 2
            if len(df_w) < target_w: target_w, target_m = len(df_w), party_capacity - len(df_w)
            elif len(df_m) < target_m: target_m, target_w = len(df_m), party_capacity - len(df_m)
            
            def do_select(df_pool, n):
                pri = df_pool[df_pool['우선순위']]
                nor = df_pool[~df_pool['우선순위']]
                sel_pri = pri.sample(n=min(len(pri), n))
                rem = n - len(sel_pri)
                if rem <= 0: return sel_pri, df_pool.drop(sel_pri.index)
                
                new, crew = nor[nor['참여이력'] == '신규'], nor[nor['참여이력'] == '크루']
                t_new, t_crew = rem // 2 + rem % 2, rem // 2
                if len(new) < t_new: t_crew += (t_new - len(new)); t_new = len(new)
                elif len(crew) < t_crew: t_new += (t_crew - len(crew)); t_crew = len(crew)
                
                sel_new = new.sample(n=min(len(new), t_new))
                sel_crew = crew.sample(n=min(len(crew), t_crew))
                sel = pd.concat([sel_pri, sel_new, sel_crew])
                return sel, df_pool.drop(sel.index)

            sel_m, wait_m = do_select(df_m, target_m)
            sel_w, wait_w = do_select(df_w, target_w)
            st.session_state['selected_df'] = pd.concat([sel_m, sel_w]).sample(frac=1).reset_index(drop=True)
            st.session_state['waitlist_df'] = pd.concat([wait_m, wait_w]).sample(frac=1).reset_index(drop=True)
            st.success(f"✅ 선발 완료! (참가: {len(st.session_state['selected_df'])}명 / 대기: {len(st.session_state['waitlist_df'])}명)")

        if 'selected_df' in st.session_state:
            def to_excel(df_in):
                output = io.BytesIO()
                # engine='xlsxwriter'를 사용하기 위해 requirements.txt에 추가 필요
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_in.drop(columns=['매칭키', '우선순위'], errors='ignore').to_excel(writer, index=False)
                return output.getvalue()
            
            col_d1, col_d2 = st.columns(2)
            with col_d1: st.download_button("📥 최종 참가자 명단 저장", to_excel(st.session_state['selected_df']), "참가자_명단.xlsx")
            with col_d2: st.download_button("📥 대기자 명단 저장", to_excel(st.session_state['waitlist_df']), "대기자_명단.xlsx")

            # ==========================================
            # 2단계: 자리 배치
            # ==========================================
            st.write("---")
            if st.button("🚀 2단계: 선발된 인원으로 자리 배치 생성", use_container_width=True):
                sel_list = st.session_state['selected_df'].to_dict('records')
                for idx, p in enumerate(sel_list): p['고유ID'] = f"{p['이름']}_{idx}"
                
                results = generate_full_schedule(sel_list, table_count)
                st.success("🎉 배치 완료!")
                
                tabs = st.tabs([f"{i+1}라운드" for i in range(len(results))])
                for i, tab in enumerate(tabs):
                    with tab:
                        cols = st.columns(3)
                        for t_idx, table in enumerate(results[i]):
                            with cols[t_idx % 3]:
                                st.markdown(f"**📍 {t_idx+1}번 테이블**")
                                st.dataframe(pd.DataFrame(table)[['이름', '성별', '소속학교']], hide_index=True)
                
                # 개인별 텍스트 출력 로직 (기존과 동일)
                final_rows = []
                for p in sel_list:
                    row = {"이름": p['이름'], "성별": p['성별'], "학교": p['소속학교']}
                    for r_idx, rnd in enumerate(results):
                        for t_idx, t in enumerate(rnd):
                            if any(x['고유ID'] == p['고유ID'] for x in t):
                                row[f"{r_idx+1}R"] = f"{t_idx+1}번"
                    final_rows.append(row)
                st.dataframe(pd.DataFrame(final_rows), use_container_width=True)
