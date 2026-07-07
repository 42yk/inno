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
    """새로운 프롬프트를 추가합니다."""
    print("\n=== 프롬프트 추가 ===")
    
    # 제목 입력
    while True:
        title = input("제목: ").strip()
        if title:
            break
        print("[경고] 제목은 비어있을 수 없습니다. 다시 입력해주세요.")

    # 내용 입력
    while True:
        content = input("내용: ").strip()
        if content:
            break
        print("[경고] 내용은 비어있을 수 없습니다. 다시 입력해주세요.")

    # 카테고리 선택
    print("\n--- 카테고리 목록 ---")
    for idx, cat in enumerate(CATEGORIES, 1):
        print(f"{idx}. {cat}")
    print("7. 직접 입력")
    
    while True:
        cat_choice = input("카테고리 선택(번호 입력): ").strip()
        if cat_choice in [str(i) for i in range(1, 7)]:
            category = CATEGORIES[int(cat_choice) - 1]
            break
        elif cat_choice == "7":
            while True:
                category = input("새 카테고리 이름: ").strip()
                if category:
                    break
                print("[경고] 카테고리 이름은 비어있을 수 없습니다.")
            break
        else:
            print("[경고] 올바른 번호(1~7)를 입력해주세요.")

    # 고유 ID 생성 (최대 ID + 1)
    new_id = max([p.get("id", 0) for p in prompts]) + 1 if prompts else 1

    # 새 프롬프트 객체 생성
    new_prompt = {
        "id": new_id,
        "title": title,
        "content": content,
        "category": category,
        "favorite": False,
        "views": 0
    }
    
    prompts.append(new_prompt)
    prompt_storage.save_to_json(DATA_FILE, prompts)
    print(f"\n[성공] '{title}' 프롬프트가 추가되었습니다. (ID: {new_id})")


def show_list(prompts):
    """프롬프트 목록을 보여줍니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다. 먼저 프롬프트를 추가해주세요.")
        return

    print("\n--- 정렬 조건 선택 ---")
    print("1. 등록순 (기본)")
    print("2. 인기순 (조회수 기준)")
    sort_choice = input("선택: ").strip()

    # 정렬 처리
    if sort_choice == "2":
        display_list = sorted(prompts, key=lambda x: (-x.get("views", 0), x.get("id", 0)))
        print("\n=== 프롬프트 목록 (인기순) ===")
    else:
        display_list = sorted(prompts, key=lambda x: x.get("id", 0))
        print("\n=== 프롬프트 목록 (등록순) ===")

    for idx, p in enumerate(display_list, 1):
        fav_star = " ⭐" if p.get("favorite") else ""
        views_count = f" [조회수: {p.get('views', 0)}회]"
        print(f"{idx}. [{p.get('category')}] {p.get('title')}{fav_star}{views_count}")

    print(f"\n총 {len(display_list)}개의 프롬프트")



def show_category_prompts(prompts):
    """카테고리별로 프롬프트를 필터링하여 조회합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    # 현재 존재하는 모든 카테고리 추출 (중복 제거)
    existing_categories = sorted(list(set([p.get("category") for p in prompts if p.get("category")])))
    
    if not existing_categories:
        print("\n[안내] 카테고리 정보가 없습니다.")
        return

    print("\n=== 카테고리별 조회 ===")
    for idx, cat in enumerate(existing_categories, 1):
        print(f"{idx}. {cat}")
        
    while True:
        choice = input("조회할 카테고리 번호: ").strip()
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(existing_categories):
                selected_cat = existing_categories[choice_idx]
                break
            else:
                print("[경고] 올바른 범위의 번호를 입력해주세요.")
        except ValueError:
            print("[경고] 숫자를 입력해주세요.")

    filtered = [p for p in prompts if p.get("category") == selected_cat]
    
    print(f"\n=== 카테고리 [{selected_cat}] 조회 결과 ===")
    for idx, p in enumerate(filtered, 1):
        fav_star = " ⭐" if p.get("favorite") else ""
        print(f"{idx}. {p.get('title')}{fav_star} [조회수: {p.get('views', 0)}회]")
        
    print(f"\n총 {len(filtered)}개의 프롬프트")

def search_prompts(prompts):
    """키워드를 입력받아 제목 또는 내용에 포함된 프롬프트를 검색합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    print("\n=== 프롬프트 검색 ===")
    keyword = input("검색 키워드 입력: ").strip()
    if not keyword:
        print("[경고] 키워드가 입력되지 않아 검색을 취소합니다.")
        return

    filtered = []
    for p in prompts:
        title = p.get("title", "")
        content = p.get("content", "")
        if keyword.lower() in title.lower() or keyword.lower() in content.lower():
            filtered.append(p)

    if not filtered:
        print(f"\n[안내] '{keyword}' 키워드를 포함하는 프롬프트가 없습니다.")
        return

    print(f"\n=== '{keyword}' 검색 결과 (총 {len(filtered)}개) ===")
    for idx, p in enumerate(filtered, 1):
        fav_star = " ⭐" if p.get("favorite") else ""
        print(f"{idx}. [{p.get('category')}] {p.get('title')}{fav_star} [조회수: {p.get('views', 0)}회]")


def show_prompt_detail(prompts):
    """프롬프트 상세 정보를 조회하고 수정/삭제 서브 메뉴를 제공합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    print("\n=== 프롬프트 상세 보기 ===")
    id_input = input("조회할 프롬프트 ID 입력: ").strip()
    
    # ID를 통한 프롬프트 검색
    target_prompt = None
    try:
        target_id = int(id_input)
        for p in prompts:
            if p.get("id") == target_id:
                target_prompt = p
                break
    except ValueError:
        print("[경고] 올바른 형식의 ID(숫자)를 입력해주세요.")
        return

    if not target_prompt:
        print(f"[경고] ID가 {id_input}인 프롬프트를 찾을 수 없습니다.")
        return

    # 상세 조회 시 조회수 누적 (+1)
    target_prompt["views"] = target_prompt.get("views", 0) + 1
    prompt_storage.save_to_json(DATA_FILE, prompts)

    while True:
        # 상세 정보 출력
        print("\n" + "─" * 40)
        print(f"ID: {target_prompt.get('id')}")
        print(f"제목: {target_prompt.get('title')}")
        print(f"카테고리: {target_prompt.get('category')}")
        print(f"즐겨찾기: {'⭐' if target_prompt.get('favorite') else '☆'}")
        print(f"조회수: {target_prompt.get('views')}회")
        print("─" * 40)
        print("내용:")
        print(target_prompt.get("content"))
        print("─" * 40)

        # 서브 메뉴
        print("1. 수정")
        print("2. 삭제")
        print("3. 이전 메뉴로")
        sub_choice = input("선택: ").strip()

        match sub_choice:
            case "1":
                # 수정 기능
                print("\n=== 프롬프트 수정 ===")
                print("(수정하지 않으려면 그냥 Enter키를 누르세요)")
                new_title = input(f"새 제목 [{target_prompt.get('title')}]: ").strip()
                new_content = input(f"새 내용 (기존 내용 유지 시 Enter): ").strip()
                
                print(f"현재 카테고리: {target_prompt.get('category')}")
                print("--- 카테고리 목록 ---")
                for idx, cat in enumerate(CATEGORIES, 1):
                    print(f"{idx}. {cat}")
                print("7. 직접 입력")
                print("8. 수정 안 함 (기존 유지)")
                
                new_category = None
                while True:
                    cat_choice = input("카테고리 선택(번호 입력): ").strip()
                    if not cat_choice or cat_choice == "8":
                        new_category = target_prompt.get("category")
                        break
                    elif cat_choice in [str(i) for i in range(1, 7)]:
                        new_category = CATEGORIES[int(cat_choice) - 1]
                        break
                    elif cat_choice == "7":
                        while True:
                            new_category = input("새 카테고리 이름: ").strip()
                            if new_category:
                                break
                            print("[경고] 카테고리 이름은 비어있을 수 없습니다.")
                        break
                    else:
                        print("[경고] 올바른 번호(1~8)를 입력해주세요.")

                if new_title:
                    target_prompt["title"] = new_title
                if new_content:
                    target_prompt["content"] = new_content
                target_prompt["category"] = new_category
                
                prompt_storage.save_to_json(DATA_FILE, prompts)
                print("\n[성공] 프롬프트가 수정되었습니다.")
                
            case "2":
                # 삭제 기능
                confirm = input("\n정말 이 프롬프트를 삭제하시겠습니까? (y/n): ").strip().lower()
                if confirm in ["y", "ye", "yes"]:
                    prompts.remove(target_prompt)
                    prompt_storage.save_to_json(DATA_FILE, prompts)
                    print("\n[성공] 프롬프트가 삭제되었습니다.")
                    break
                else:
                    print("\n[알림] 삭제를 취소했습니다.")
            case "3":
                break
            case _:
                print("\n[경고] 잘못된 입력입니다. 1~3 사이의 번호를 선택해주세요.")


def toggle_favorite(prompts):
    """특정 프롬프트의 즐겨찾기 설정을 해제하거나 추가합니다 (토글)."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    print("\n=== 즐겨찾기 관리 (토글) ===")
    id_input = input("즐겨찾기 상태를 변경할 프롬프트 ID 입력: ").strip()
    
    target_prompt = None
    try:
        target_id = int(id_input)
        for p in prompts:
            if p.get("id") == target_id:
                target_prompt = p
                break
    except ValueError:
        print("[경고] 올바른 형식의 ID(숫자)를 입력해주세요.")
        return

    if not target_prompt:
        print(f"[경고] ID가 {id_input}인 프롬프트를 찾을 수 없습니다.")
        return

    # 토글 처리
    target_prompt["favorite"] = not target_prompt.get("favorite", False)
    prompt_storage.save_to_json(DATA_FILE, prompts)
    status_str = "등록" if target_prompt["favorite"] else "해제"
    print(f"\n[성공] '{target_prompt.get('title')}' 프롬프트가 즐겨찾기에 {status_str}되었습니다.")

def show_favorite_prompts(prompts):
    """즐겨찾기된 프롬프트만 모아서 목록으로 출력합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    favorites = [p for p in prompts if p.get("favorite")]
    
    if not favorites:
        print("\n[안내] 즐겨찾기에 등록된 프롬프트가 없습니다. 마음에 드는 프롬프트를 즐겨찾기 해보세요!")
        return

    print("\n=== 즐겨찾기 목록 ===")
    for idx, p in enumerate(favorites, 1):
        print(f"{idx}. [{p.get('category')}] {p.get('title')} ⭐ [조회수: {p.get('views', 0)}회]")
        
    print(f"\n총 {len(favorites)}개의 즐겨찾기 프롬프트")


def export_markdown_menu(prompts):
    """프롬프트를 카테고리별로 분류하여 Markdown 파일로 내보냅니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없어 내보낼 수 없습니다.")
        return

    print("\n=== Markdown 내보내기 ===")
    default_name = "prompts.md"
    file_input = input(f"내보낼 파일명 입력 (기본값: {default_name}): ").strip()
    
    if not file_input:
        filepath = EXPORT_FILE
        filename = default_name
    else:
        if not file_input.endswith(".md"):
            file_input += ".md"
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_input)
        filename = file_input

    print(f"\n[알림] 프롬프트 보관함을 '{filename}' 파일로 내보내는 중...")
    success = prompt_storage.export_to_markdown(filepath, prompts)
    
    if success:
        print(f"[성공] 파일 내보내기가 완료되었습니다. 경로: {filepath}")
    else:
        print("[오류] 파일 내보내기에 실패했습니다.")


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
