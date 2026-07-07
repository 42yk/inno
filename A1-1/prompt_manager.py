import os
import prompt_storage

# 데이터 파일 경로 설정
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.json")
EXPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.md")

# 카테고리 정의
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]

def show_menu():
    """메인 메뉴를 콘솔에 출력합니다."""
    print("\n=== 나만의 프롬프트 관리 ===")
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 관리")
    print("7. 즐겨찾기 목록")
    print("8. Markdown 내보내기")
    print("0. 종료")
    print("===========================")

def add_prompt(prompts):
    """[뼈대] 새로운 프롬프트를 추가합니다."""
    print("\n[알림] 프롬프트 추가 기능은 준비 중입니다.")

def show_list(prompts):
    """프롬프트 목록을 보여줍니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다. 먼저 프롬프트를 추가해주세요.")
        return

    print("\n=== 프롬프트 목록 ===")
    for idx, p in enumerate(prompts, 1):
        fav_star = " ⭐" if p.get("favorite") else ""
        print(f"{idx}. [{p.get('category')}] {p.get('title')}{fav_star}")

    print(f"\n총 {len(prompts)}개의 프롬프트")


def show_category_prompts(prompts):
    """[뼈대] 카테고리별로 조회합니다."""
    print("\n[알림] 카테고리별 조회 기능은 준비 중입니다.")

def search_prompts(prompts):
    """[뼈대] 키워드로 검색합니다."""
    print("\n[알림] 검색 기능은 준비 중입니다.")

def show_prompt_detail(prompts):
    """[뼈대] 상세 보기를 지원합니다."""
    print("\n[알림] 상세 보기 기능은 준비 중입니다.")

def toggle_favorite(prompts):
    """[뼈대] 즐겨찾기를 추가하거나 해제합니다."""
    print("\n[알림] 즐겨찾기 관리 기능은 준비 중입니다.")

def show_favorite_prompts(prompts):
    """[뼈대] 즐겨찾기 목록을 조회합니다."""
    print("\n[알림] 즐겨찾기 목록 보기 기능은 준비 중입니다.")

def export_markdown_menu(prompts):
    """[뼈대] 마크다운 파일로 내보냅니다."""
    print("\n[알림] 마크다운 내보내기 기능은 준비 중입니다.")

def main():
    # 시작 시 데이터 로드
    prompts = prompt_storage.load_from_json(DATA_FILE)
    
    while True:
        show_menu()
        choice = input("선택: ").strip()
        
        match choice:
            case "1":
                add_prompt(prompts)
            case "2":
                show_list(prompts)
            case "3":
                show_category_prompts(prompts)
            case "4":
                search_prompts(prompts)
            case "5":
                show_prompt_detail(prompts)
            case "6":
                toggle_favorite(prompts)
            case "7":
                show_favorite_prompts(prompts)
            case "8":
                export_markdown_menu(prompts)
            case "0":
                print("\n프로그램을 종료합니다. 이용해 주셔서 감사합니다.")
                break
            case _:
                print("\n[경고] 잘못된 입력입니다. 0~8 사이의 번호를 입력해주세요.")

if __name__ == "__main__":
    main()
