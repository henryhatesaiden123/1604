def find_gto_blocks(b_values):
    """B열 값 리스트에서 '2'로 시작하고 '1'로 끝나는 모든 GTO 계획 블록의 인덱스를 찾습니다."""
    blocks = []
    i = 0
    while i < len(b_values):
        if b_values[i] == 2:
            start_index = i
            try:
                # 현재 위치 이후에 '1'이 있는지 찾음
                end_index = b_values.index(1, start_index + 1)
                blocks.append({"start": start_index, "end": end_index})
                i = end_index + 1 # 다음 검색은 이 블록 이후부터
            except ValueError:
                # '1'을 찾지 못하면 루프 종료
                i += 1
        else:
            i += 1
    return blocks

def check_single_gto_plan(plan):
    """하나의 GTO 계획 시퀀스를 10가지 규칙에 따라 검사합니다."""
    # 규칙 4 (예외 케이스) 먼저 확인
    if plan == [2, 4, 17, 1]:
        return True, "성공", []

    # 규칙 2, 3 (시작과 끝)
    if plan[:3] != [2, 4, 5]:
        return False, "시작은 반드시 '2-4-5'여야 합니다.", [0, 1, 2]
    if plan[-3:] not in ([5, 8, 1], [6, 17, 1]):
        return False, "마지막은 '5-8-1' 또는 '6-17-1'이어야 합니다.", [len(plan)-3, len(plan)-2, len(plan)-1]

    for i, val in enumerate(plan):
        # 규칙 1 (연속 숫자)
        if i > 0 and val == plan[i-1]:
            return False, f"숫자 '{val}'가 연속으로 나올 수 없습니다.", [i-1, i]
        # 규칙 5 (2의 위치)
        if val == 2 and i != 0:
            return False, "'2'는 계획의 시작에만 올 수 있습니다.", [i]
        # 규칙 6 (4의 위치)
        if val == 4 and i != 1:
            return False, "'4'는 계획의 두 번째에만 올 수 있습니다.", [i]
        # 규칙 10 (8, 17의 위치)
        if val in (8, 17) and i != len(plan) - 2:
            return False, f"'{val}'는 계획의 끝에서 두 번째에만 올 수 있습니다.", [i]
        # 규칙 7 (5의 선행)
        if val == 5 and i > 0 and plan[i-1] not in (4, 6):
            return False, "'5'는 '4' 또는 '6' 다음에만 올 수 있습니다.", [i-1, i]
        # 규칙 8 (6의 선행)
        if val == 6 and i > 0 and plan[i-1] not in (5, 7):
            return False, "'6'는 '5' 또는 '7' 다음에만 올 수 있습니다.", [i-1, i]
        # 규칙 9 (7의 규칙)
        if val == 7:
            if i == 0 or plan[i-1] != 5:
                return False, "'7'은 반드시 '5' 다음에 와야 합니다.", [i-1, i]
            if i == len(plan) - 1 or plan[i+1] != 6:
                return False, "'7' 다음에는 반드시 '6'이 와야 합니다.", [i, i+1]

    return True, "성공", []

def validate_gto_logic(app_instance, line_data_model, app_mode_value):
    """GTO-W 모드일 때 모든 GTO 계획의 유효성을 검사하고 UI에 피드백합니다."""
    if app_mode_value != "GTO-W 감시용":
        return

    # 1. 모든 B열 배경색을 기본으로 초기화
    for line_entry in app_instance.line_entries:
        line_entry["button"].config(bg="#333333")

    # 2. B열 값들을 숫자 리스트로 변환
    b_values = line_data_model.get_all_b_values()

    # 3. GTO 계획 블록 찾기
    gto_blocks = find_gto_blocks(b_values)

    # 4. 각 블록을 검사하고 결과 처리
    for block in gto_blocks:
        start, end = block["start"], block["end"]
        plan_sequence = b_values[start : end + 1]
        
        is_valid, message, error_indices = check_single_gto_plan(plan_sequence)

        if is_valid:
            for i in range(start, end + 1):
                app_instance.line_entries[i]["button"].config(bg="#2E7D32") # 성공: 녹색
                app_instance.run_line(i)
        else:
            app_instance.push_error(f"{start+1}번 레일 계획 오류: {message}")
            for i in range(start, end + 1):
                app_instance.stop_line(i) # 실패 시 실행 중지
            for error_idx in error_indices:
                # 절대 인덱스로 변환하여 UI에 반영
                app_instance.line_entries[start + error_idx]["button"].config(bg="#D32F2F") # 실패: 붉은색