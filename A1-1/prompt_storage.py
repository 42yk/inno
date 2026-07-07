import json
import os

DEFAULT_PROMPTS = [
    {
        "id": 1,
        "title": "블로그 글 작성 도우미",
        "content": "당신은 10년 경력의 전문 블로거입니다.\n주어진 주제에 대해 SEO에 최적화된 블로그 글을 작성해주세요.\n서론, 본론, 결론 구조를 갖추고, 독자의 관심을 끄는 제목을 3개 제안해주세요.",
        "category": "텍스트 생성",
        "favorite": True,
        "views": 0
    },
    {
        "id": 2,
        "title": "제품 썸네일 생성",
        "content": "다음 제품의 매력적인 썸네일 이미지를 생성해주세요. 제품의 핵심 기능과 브랜딩이 잘 드러나야 합니다. 텍스트는 최소화하고 시각적 대비를 극대화해주세요.",
        "category": "이미지 생성",
        "favorite": False,
        "views": 0
    },
    {
        "id": 3,
        "title": "IT 컨설턴트 페르소나",
        "content": "당신은 20년 경력의 베테랑 IT 컨설턴트입니다. 클라이언트의 인프라 개선 및 클라우드 마이그레이션 제안에 대해 전문적이고 직관적인 피드백을 제시해주세요.",
        "category": "페르소나",
        "favorite": False,
        "views": 0
    }
]

def load_from_json(file_path):
    """JSON 파일에서 프롬프트 데이터를 불러옵니다. 파일이 없으면 기본 데이터를 반환하고 새로 저장합니다."""
    if not os.path.exists(file_path):
        save_to_json(file_path, DEFAULT_PROMPTS)
        return list(DEFAULT_PROMPTS)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"\n[오류] JSON 불러오기 중 오류가 발생했습니다: {e}")
        return list(DEFAULT_PROMPTS)

def save_to_json(file_path, data):
    """프롬프트 데이터를 JSON 파일로 저장합니다."""
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"\n[오류] JSON 저장 중 오류가 발생했습니다: {e}")
        return False

def export_to_markdown(file_path, data):
    """프롬프트 데이터를 카테고리별로 분류하여 깔끔한 Markdown 파일로 내보냅니다."""
    try:
        categorized = {}
        for prompt in data:
            cat = prompt.get("category", "기타")
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(prompt)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 📂 내 프롬프트 보관함\n\n")
            f.write("이 문서는 프롬프트 관리 프로그램에서 내보낸 결과 파일입니다.\n\n")
            
            for cat in sorted(categorized.keys()):
                f.write(f"## ■ {cat}\n\n")
                for p in categorized[cat]:
                    fav_icon = " ⭐" if p.get("favorite") else ""
                    f.write(f"### {p.get('title')}{fav_icon}\n")
                    f.write(f"- **ID**: {p.get('id')}\n")
                    f.write(f"- **조회수**: {p.get('views', 0)}회\n")
                    f.write("- **내용**:\n")
                    
                    content_lines = p.get('content', '').split('\n')
                    formatted_content = "\n".join([f"  > {line}" for line in content_lines])
                    f.write(f"{formatted_content}\n\n")
                    f.write("---\n\n")
        return True
    except Exception as e:
        print(f"\n[오류] Markdown 내보내기 중 오류가 발생했습니다: {e}")
        return False
