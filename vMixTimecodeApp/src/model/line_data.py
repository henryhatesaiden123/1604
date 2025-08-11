class LineDataModel:
    def __init__(self):
        self.rail_count = 30  # 기본값
        self.lines = []       # 라인 데이터 저장
        self._initialize_lines()

    def _initialize_lines(self):
        # 실제 애플리케이션에서는 설정 파일 등에서 로드할 수 있습니다.
        # 여기서는 임시로 빈 라인 데이터를 생성합니다.
        for i in range(self.rail_count):
            self.lines.append({
                "time": "00:00:00",
                "preview": "",
                "button": "0",
                "comment": "",
                "input": "",
                "description": ""
            })

    def get_line_data(self, index):
        if 0 <= index < len(self.lines):
            return self.lines[index]
        return None

    def update_line_data(self, index, key, value):
        if 0 <= index < len(self.lines):
            self.lines[index][key] = value
            return True
        return False

    def get_all_b_values(self):
        return [int(line["button"]) if line["button"].isdigit() else 0 for line in self.lines]
