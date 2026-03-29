import streamlit as st
import pandas as pd
import random
import io

st.set_page_config(page_title="청취담 연합파티 매칭", page_icon="🍻", layout="wide")

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

st.title("🍻 청취담 연합파티 스케줄러 (사전 배치용)")
st.subheader("교통대 x 건국대 글로컬 캠퍼스")

# --- 1. 사이드바 설정 ---
st.sidebar.header("⚙️ 파티 설정")
party_capacity = st.sidebar.number_input("이번 파티 참가 정원 (명)", min_value=4, value=48, step=1)
table_count = st.sidebar.number_input("준비된 테이블 개수", min_value=1, value=12, step=1)

# --- 2. 전체 스케줄 생성 알고리즘 (N개 대학 동적 분산 및 과거 이력 연동) ---
def generate_full_schedule(people_list, num_tables, past_met_pairs=None, total_rounds=3):
    n = len(people_list)
    base_size = n // num_tables
    remainder = n % num_tables
    table_sizes = [base_size + 1 if i < remainder else base_size for i in range(num_tables)]

    total_m = sum(1 for p in people_list if p['성별'] == '남')
    total_w = sum(1 for p in people_list if p['성별'] == '여')

    min_w = total_w // num_tables
    max_w = (total_w + num_tables - 1) // num_tables if num_tables else 0
    min_m = total_m // num_tables
    max_m = (total_m + num_tables - 1) // num_tables if num_tables else 0
    
    # [핵심 1] 동적 N개 대학 자동 인식 및 수학적 할당량 계산
    unique_univs = set(p['소속학교'] for p in people_list)
    univ_counts = {u: sum(1 for p in people_list if p['소속학교'] == u) for u in unique_univs}
    min_u = {u: count // num_tables for u, count in univ_counts.items()}
    max_u = {u: (count + num_tables - 1) // num_tables if num_tables else 0 for u, count in univ_counts.items()}

    best_all_rounds = []
    global_min_penalty = float('inf')

    for attempt in range(50): 
        # [핵심 2] 과거 파티에서 만났던 기록을 현재 패널티(met_pairs)에 주입
        met_pairs = set(past_met_pairs) if past_met_pairs else set()
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
                        
                        # [핵심 3] 동적 N개 대학 현재 테이블 인원 스캔
                        temp_univ_counts = {u: sum(1 for x in round_tables[t_idx] if x['소속학교'] == u) for u in unique_univs}
                        temp_univ_counts[p['소속학교']] += 1

                        if temp_w > max_w: p_penalty += 50000
                        if temp_m > max_m: p_penalty += 50000
                        # N개 대학 정원 통제 적용
                        for u in unique_univs:
                            if temp_univ_counts[u] > max_u[u]: p_penalty += 50000
                            
                        if p['성별'] == '여':
                            unseated_w = sum(1 for x in unseated if x['성별'] == '여')
                            tables_needing_w = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '여') < min_w)
                            if (temp_w - 1) >= min_w and unseated_w <= tables_needing_w: p_penalty += 50000
                        elif p['성별'] == '남':
                            unseated_m = sum(1 for x in unseated if x['성별'] == '남')
                            tables_needing_m = sum(1 for t in round_tables if sum(1 for x in t if x['성별'] == '남') < min_m)
                            if (temp_m - 1) >= min_m and unseated_m <= tables_needing_m: p_penalty += 50000
                            
                        # [핵심 4] N개 대학별 고갈 방지 (Starvation Prevention)
                        curr_u = p['소속학교']
                        unseated_curr_u = sum(1 for x in unseated if x['소속학교'] == curr_u)
                        tables_needing_curr_u = sum(1 for t in round_tables if sum(1 for x in t if x['소속학교'] == curr_u) < min_u[curr_u])
                        if (temp_univ_counts[curr_u] - 1) >= min_u[curr_u] and unseated_curr_u <= tables_needing_curr_u:
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
        if global_min_penalty == 0: break
    return best_all_rounds

# --- 3. 메인 화면 ---
st.write("---")
st.write("### 📂 참가자 명단 업로드")

col_u1, col_u2 = st.columns(2)
with col_u1:
    uploaded_file = st.file_uploader("📂 [필수] 이번 파티 전체 신청자 명단 (엑셀/CSV)", type=['xlsx', 'csv'])
with col_u2:
    past_waitlist_file = st.file_uploader("📂 [선택] 저번 파티 미선정자/대기자 명단 (우선선발용)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    target_keywords = ['이름', '성별', '소속학교', '학과', '학년', '참여이력', '신규']
    rename_dict = {}

    for keyword in target_keywords:
        matched_col = next((col for col in df.columns if keyword in str(col)), None)
        if matched_col and matched_col != keyword:
            if keyword == '신규': rename_dict[matched_col] = '참여이력'
            else: rename_dict[matched_col] = keyword
            
    if rename_dict:
        df = df.rename(columns=rename_dict)

    if not {'이름', '성별', '소속학교'}.issubset(df.columns):
        st.error("⚠️ 파일 첫 줄에 최소한 '이름', '성별', '소속학교' 관련 단어가 포함되어 있는지 확인해주세요!")
    else:
        # 데이터 자동 정제
        df['성별'] = df['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
        df['소속학교'] = df['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
        
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
            
        if '참여이력' not in df.columns:
            df['참여이력'] = '신규' 
        else:
            df['참여이력'] = df['참여이력'].astype(str).apply(lambda x: '크루' if '크루' in x or '기존' in x else '신규')
        
        # ==========================================
        # [복구 완] 대시보드 통계 계산 및 UI 출력 (비율 포함)
        # ==========================================
        total_count = len(df)
        
        total_m_count = len(df[df['성별'] == '남'])
        total_w_count = len(df[df['성별'] == '여'])
        ratio_m = (total_m_count / total_count) * 100 if total_count > 0 else 0
        ratio_w = (total_w_count / total_count) * 100 if total_count > 0 else 0
        
        total_sch_a_count = len(df[df['소속학교'] == '교통대'])
        total_sch_b_count = len(df[df['소속학교'] == '건국대'])
        ratio_sch_a = (total_sch_a_count / total_count) * 100 if total_count > 0 else 0
        ratio_sch_b = (total_sch_b_count / total_count) * 100 if total_count > 0 else 0
        
        st.write(f"✅ **총 신청자 수: {total_count}명** (설정된 파티 정원: {party_capacity}명)")
        st.info(f"📊 **신청자 성비:** 👨 남성 {total_m_count}명 ({ratio_m:.1f}%) / 👩‍🦰 여성 {total_w_count}명 ({ratio_w:.1f}%)")
        st.info(f"🏫 **소속학교 비율:** 🚆 교통대 {total_sch_a_count}명 ({ratio_sch_a:.1f}%) / 🐂 건국대 {total_sch_b_count}명 ({ratio_sch_b:.1f}%)")
        
        if has_grade:
            grade_counts = df[df['학년'] != '미기재']['학년'].value_counts().sort_index()
            if not grade_counts.empty:
                grade_stats_str = " / ".join([f"{grade} {count}명 ({(count/total_count)*100:.1f}%)" for grade, count in grade_counts.items()])
                st.info(f"🎓 **학년별 비율:** {grade_stats_str}")
        
        # 과거 대기자 처리 (우선 선발용)
        df['매칭키'] = df['이름'].astype(str) + df['성별'].astype(str) + df['소속학교'].astype(str)
        past_keys = set()
        if past_waitlist_file is not None:
            if past_waitlist_file.name.endswith('.csv'): df_past = pd.read_csv(past_waitlist_file)
            else: df_past = pd.read_excel(past_waitlist_file)
            try:
                df_past['성별'] = df_past['성별'].astype(str).apply(lambda x: '남' if '남' in x else ('여' if '여' in x else x))
                df_past['소속학교'] = df_past['소속학교'].astype(str).apply(lambda x: '교통대' if '교통' in x else ('건국대' if '건국' in x else x))
                df_past['매칭키'] = df_past['이름'].astype(str) + df_past['성별'].astype(str) + df_past['소속학교'].astype(str)
                past_keys = set(df_past['매칭키'].dropna().tolist())
                st.success(f"✅ 저번 대기자 {len(past_keys)}명을 성공적으로 인식했습니다. (우선 선발 대상)")
            except:
                st.warning("⚠️ 저번 대기자 파일의 형식이 맞지 않아 우선 선발을 생략합니다.")
        
        # ==========================================
        # 1단계: 참가자 랜덤 선발 및 대기자 추출
        # ==========================================
        st.write("---")
        if st.button("🚀 1단계: 참가 정원에 맞춰 최종 참가자/대기자 선발", use_container_width=True):
            with st.spinner("정원과 성비에 맞춰 최적의 참가자를 선발 중입니다..."):
                df['우선순위'] = df['매칭키'].apply(lambda x: True if x in past_keys else False)
                
                df_m = df[df['성별'] == '남'].copy()
                df_w = df[df['성별'] == '여'].copy()
                
                target_m = party_capacity // 2
                target_w = party_capacity // 2
                
                # 유연한 성비 보정 로직
                if len(df_w) < target_w:
                    target_w = len(df_w)
                    target_m = party_capacity - target_w 
                elif len(df_m) < target_m:
                    target_m = len(df_m)
                    target_w = party_capacity - target_m 
                    
                target_m = min(target_m, len(df_m))
                target_w = min(target_w, len(df_w))

                def safe_sample(data_frame, n):
                    n = min(n, len(data_frame))
                    if n > 0: return data_frame.sample(n=n, random_state=random.randint(1,10000))
                    return pd.DataFrame(columns=data_frame.columns)

                def select_participants(df_pool, target_count):
                    df_priority = df_pool[df_pool['우선순위'] == True]
                    df_normal = df_pool[df_pool['우선순위'] == False]
                    
                    selected_priority = safe_sample(df_priority, target_count)
                    remaining_target = target_count - len(selected_priority)
                    
                    if remaining_target <= 0:
                        return selected_priority, df_pool.drop(selected_priority.index)
                        
                    df_new = df_normal[df_normal['참여이력'] == '신규']
                    df_crew = df_normal[df_normal['참여이력'] == '크루']
                    
                    target_new = remaining_target // 2 + remaining_target % 2 
                    target_crew = remaining_target // 2
                    
                    # Spill-over (부족한 쪽의 남는 자리를 다른 쪽으로)
                    if len(df_new) < target_new:
                        target_crew += (target_new - len(df_new))
                        target_new = len(df_new)
                    elif len(df_crew) < target_crew:
                        target_new += (target_crew - len(df_crew))
                        target_crew = len(df_crew)
                        
                    selected_new = safe_sample(df_new, target_new)
                    selected_crew = safe_sample(df_crew, target_crew)
                    
                    final_selected = pd.concat([selected_priority, selected_new, selected_crew])
                    final_waitlisted = df_pool.drop(final_selected.index)
                    return final_selected, final_waitlisted

                selected_m, waitlist_m = select_participants(df_m, target_m)
                selected_w, waitlist_w = select_participants(df_w, target_w)
                
                final_selected_df = pd.concat([selected_m, selected_w]).sample(frac=1).reset_index(drop=True)
                final_waitlist_df = pd.concat([waitlist_m, waitlist_w]).sample(frac=1).reset_index(drop=True)
                
                # 다음 단계를 위해 Session State에 저장
                st.session_state['selected_df'] = final_selected_df
                st.session_state['waitlist_df'] = final_waitlist_df
                st.success("🎉 참가자 선발 및 대기자 추출이 완료되었습니다! 아래 결과를 확인해주세요.")

        # 1단계 선발이 완료되어 Session State에 데이터가 있는 경우 다운로드 버튼 및 2단계 표시
        if 'selected_df' in st.session_state:
            sel_df = st.session_state['selected_df']
            wait_df = st.session_state['waitlist_df']
            
            st.info(f"🎯 **최종 선발 완료 ({len(sel_df)}명):** 👨 남성 {len(sel_df[sel_df['성별']=='남'])}명 / 👩‍🦰 여성 {len(sel_df[sel_df['성별']=='여'])}명")
            if len(wait_df) > 0:
                st.warning(f"⏳ **대기자 발생 ({len(wait_df)}명)** - 아래 버튼을 눌러 대기자 명단을 엑셀로 저장하세요.")
            
            # 엑셀 다운로드 (에러 방지를 위해 engine 제거)
            def to_excel(df_to_save):
                output = io.BytesIO()
                with pd.ExcelWriter(output) as writer:
                    df_to_save.drop(columns=['매칭키', '우선순위'], errors='ignore').to_excel(writer, index=False, sheet_name='Sheet1')
                return output.getvalue()

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.download_button(label="📥 최종 참가자 명단 엑셀 다운로드", data=to_excel(sel_df), file_name='파티_최종참가자명단.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            with col_btn2:
                st.download_button(label="📥 대기자 명단 엑셀 다운로드", data=to_excel(wait_df), file_name='파티_대기자명단.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            # ==========================================
            # 2단계: 자리 배치 (과거 이력 연동)
            # ==========================================
            st.write("---")
            st.write("### 🔀 2단계: 과거 이력 연동 및 자리 배치 생성")
            st.info("💡 과거 파티에서 만났던 사람들을 절대 다시 만나지 않도록 방어하고, N개의 대학을 균형 있게 분산합니다.")
            
            past_seat_file = st.file_uploader("📂 [선택] 저번 파티 '자리배치 결과표' (과거 중복 만남 원천 차단용)", type=['xlsx', 'csv'])

            if st.button("🚀 2단계: 선발된 참가자로 전체 라운드(1~3) 배치 구동!", use_container_width=True):
                with st.spinner('수만 가지의 경우의 수를 분석하여 최적의 동선을 계산 중입니다...'):
                    sel_list = st.session_state['selected_df'].to_dict('records')
                    
                    # 1. 현재 파티원의 고유 식별 체계 생성
                    key_to_uid = {}
                    for idx, p in enumerate(sel_list): 
                        p['고유ID'] = f"{p['이름']}_{idx}"
                        # 과거 데이터와 대조하기 위한 절대 매칭키
                        matching_key = f"{p['이름']}_{p['소속학교']}_{p['성별']}"
                        key_to_uid[matching_key] = p['고유ID']
                        
                    # 2. 과거 파티 자리배치표 파싱 로직
                    past_met_pairs = set()
                    if past_seat_file is not None:
                        try:
                            df_ps = pd.read_csv(past_seat_file) if past_seat_file.name.endswith('.csv') else pd.read_excel(past_seat_file)
                            # '라운드' 또는 'R'이 들어간 컬럼을 모두 라운드 정보로 인식
                            round_cols = [c for c in df_ps.columns if '라운드' in c or 'R' in c]
                            df_ps['매칭키'] = df_ps['이름'].astype(str) + "_" + df_ps['재학중인대학'].astype(str) + "_" + df_ps['성별'].astype(str)
                            
                            for r_col in round_cols:
                                # 같은 라운드에서 같은 테이블(값)을 가진 사람들끼리 그룹핑
                                for table_name, group in df_ps.groupby(r_col):
                                    members = group['매칭키'].dropna().tolist()
                                    # 테이블 내 모든 인원의 쌍(Pair) 생성
                                    for i in range(len(members)):
                                        for j in range(i+1, len(members)):
                                            p1_key, p2_key = members[i], members[j]
                                            # 두 명 모두 '이번 파티'에 합격하여 참가한 경우에만 패널티 등록
                                            if p1_key in key_to_uid and p2_key in key_to_uid:
                                                past_met_pairs.add(tuple(sorted([key_to_uid[p1_key], key_to_uid[p2_key]])))
                            
                            st.success(f"✅ 과거 이력 스캔 성공! 총 {len(past_met_pairs)}개의 '과거 만남 기록'을 이번 파티에서 원천 차단합니다.")
                        except Exception as e:
                            st.warning("⚠️ 과거 자리배치표 형식을 인식할 수 없어 중복 만남 방지를 생략합니다.")
                    
                    # 3. 알고리즘 최종 구동 (과거 만남 기록 주입)
                    results = generate_full_schedule(sel_list, table_count, past_met_pairs=past_met_pairs)
                    st.success("🎉 파티 전체 스케줄 배치가 완료되었습니다!")
                    
                    # (이후 하단 라운드별 표 출력 및 개인별 스케줄 로직은 기존 코드 그대로 유지)
                    
                    st.write("### 🗺️ 라운드별 테이블 배치도 (운영진용)")
                    st.info("아래 각 라운드 탭을 클릭하여 테이블별 착석 인원 정보를 확인하세요.")
                    
                    tabs = st.tabs([f"{r + 1}라운드" for r in range(len(all_rounds_data))])
                    
                    # 출력할 컬럼 동적 설정 (복구 완)
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
                    
                    # 개인별 스케줄 로직 (복구 완)
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
                    
                    st.write("### 📋 개인별 파티 스케줄표 (전체 참가자 명단)")
                    st.dataframe(result_df, hide_index=True, use_container_width=True)
                    
                    # [신규 추가] 대기자가 존재할 경우 스케줄표 바로 밑에 표로 띄워줌
                    if 'waitlist_df' in st.session_state and len(st.session_state['waitlist_df']) > 0:
                        st.write("### ⏳ 대기자 명단 (미선정자)")
                        # 불필요한 계산용 열(매칭키, 우선순위 등)은 숨기고 예쁘게 출력
                        display_wait_df = st.session_state['waitlist_df'].drop(columns=['매칭키', '우선순위', '고유ID'], errors='ignore')
                        st.dataframe(display_wait_df, hide_index=True, use_container_width=True)
                    
                    st.write("---")
                    st.write("### 📝 개별 안내용 텍스트 (복사해서 카톡 전송용)")
                    
                    text_output = ""
                    for index, row in result_df.iterrows():
                        text_output += f"{row['번호']}. {row['이름']}\n"
                        text_output += f"- 첫번째 테이블: {row['1라운드 테이블']}\n"
                        text_output += f"- 두번째 테이블: {row['2라운드 테이블']}\n"
                        text_output += f"- 세번째 테이블: {row['3라운드 테이블']}\n\n"
                    
                    st.text_area("아래 내용을 전체 복사하세요.", text_output, height=300)
