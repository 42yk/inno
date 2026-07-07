import os

import prompt_storage
from category_actions import show_category_prompts
from export_actions import export_markdown_menu
from favorite_actions import show_favorite_prompts, toggle_favorite
from prompt_actions import add_prompt, search_prompts, show_list, show_prompt_detail


# 데이터 파일 경로 설정
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.json")
EXPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.md")


# 사용자가 선택할 수 있는 메인 메뉴를 출력하는 함수입니다.
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


# 프로그램 시작 시 데이터를 불러오고 메인 메뉴 루프를 실행하는 함수입니다.
def main():
    # 시작 시 데이터 로드
    prompts = prompt_storage.load_from_json(DATA_FILE)

    while True:
        show_menu()
        choice = input("선택: ").strip()

        match choice:
            case "1":
                add_prompt(prompts, DATA_FILE)
            case "2":
                show_list(prompts)
            case "3":
                show_category_prompts(prompts)
            case "4":
                search_prompts(prompts)
            case "5":
                show_prompt_detail(prompts, DATA_FILE)
            case "6":
                toggle_favorite(prompts, DATA_FILE)
            case "7":
                show_favorite_prompts(prompts)
            case "8":
                export_markdown_menu(prompts, EXPORT_FILE)
            case "0":
                print("\n프로그램을 종료합니다. 이용해 주셔서 감사합니다.")
                break
            case _:
                print("\n[경고] 잘못된 입력입니다. 0~8 사이의 번호를 입력해주세요.")


if __name__ == "__main__":
    try:
        main()
    except EOFError:
        print("\n\n[알림] Ctrl+D가 입력되어 프로그램을 종료합니다.")
    except KeyboardInterrupt:
        print("\n\n[알림] Ctrl+C가 입력되어 프로그램을 종료합니다.")
