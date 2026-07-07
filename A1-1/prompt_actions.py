import prompt_storage


# 카테고리 정의
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]


# 프롬프트 목록을 ID 기준 등록순으로 정렬하는 함수입니다.
def get_sorted_prompts(prompts):
    """등록순(ID 기준)으로 정렬된 프롬프트 목록을 반환합니다."""
    return sorted(prompts, key=lambda x: x.get("id", 0))


# 기본 카테고리와 사용자가 직접 추가한 카테고리를 합쳐 선택 목록을 만드는 함수입니다.
def get_category_options(prompts):
    """기본 카테고리와 사용자가 직접 추가한 카테고리를 함께 반환합니다."""
    custom_categories = sorted({
        p.get("category")
        for p in prompts
        if p.get("category") and p.get("category") not in CATEGORIES
    })
    return CATEGORIES + custom_categories


# 목록 화면에서 프롬프트의 핵심 정보를 한 줄로 출력하는 함수입니다.
def print_prompt_summary(index, prompt, show_id=True):
    """목록 화면에서 공통으로 사용하는 프롬프트 한 줄 요약을 출력합니다."""
    fav_star = " ⭐" if prompt.get("favorite") else ""
    views_count = f" [조회수: {prompt.get('views', 0)}회]"
    id_text = f"(ID: {prompt.get('id')}) " if show_id else ""
    print(f"{index}. {id_text}[{prompt.get('category')}] {prompt.get('title')}{fav_star}{views_count}")


# 화면에 표시된 번호를 입력받아 실제 프롬프트 데이터를 선택하는 함수입니다.
def select_prompt_by_number(prompts, title, action_label):
    """화면에 표시된 목록 번호로 프롬프트를 선택합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return None

    display_list = get_sorted_prompts(prompts)
    print(f"\n=== {title} ===")
    for idx, prompt in enumerate(display_list, 1):
        print_prompt_summary(idx, prompt)

    choice = input(f"{action_label} 번호 입력: ").strip()
    try:
        choice_idx = int(choice) - 1
    except ValueError:
        print("[경고] 올바른 형식의 번호(숫자)를 입력해주세요.")
        return None

    if 0 <= choice_idx < len(display_list):
        return display_list[choice_idx]

    print(f"[경고] 목록에 {choice}번 프롬프트가 없습니다.")
    return None


# 사용자 입력을 받아 새 프롬프트를 생성하고 JSON 저장소에 반영하는 함수입니다.
def add_prompt(prompts, data_file):
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
    prompt_storage.save_to_json(data_file, prompts)
    print(f"\n[성공] '{title}' 프롬프트가 추가되었습니다. (ID: {new_id})")


# 전체 프롬프트 목록을 등록순 또는 인기순으로 출력하는 함수입니다.
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
        display_list = get_sorted_prompts(prompts)
        print("\n=== 프롬프트 목록 (등록순) ===")

    for idx, p in enumerate(display_list, 1):
        print_prompt_summary(idx, p)

    print(f"\n총 {len(display_list)}개의 프롬프트")


# 키워드로 제목 또는 내용이 일치하는 프롬프트를 검색하는 함수입니다.
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
        print_prompt_summary(idx, p)


# 선택한 프롬프트의 상세 정보 출력과 수정/삭제 메뉴를 처리하는 함수입니다.
def show_prompt_detail(prompts, data_file):
    """프롬프트 상세 정보를 조회하고 수정/삭제 서브 메뉴를 제공합니다."""
    target_prompt = select_prompt_by_number(prompts, "프롬프트 상세 보기", "조회할 프롬프트")
    if not target_prompt:
        return

    # 상세 조회 시 조회수 누적 (+1)
    target_prompt["views"] = target_prompt.get("views", 0) + 1
    prompt_storage.save_to_json(data_file, prompts)

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
                new_content = input("새 내용 (기존 내용 유지 시 Enter): ").strip()

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

                prompt_storage.save_to_json(data_file, prompts)
                print("\n[성공] 프롬프트가 수정되었습니다.")

            case "2":
                # 삭제 기능
                confirm = input("\n정말 이 프롬프트를 삭제하시겠습니까? (y/n): ").strip().lower()
                if confirm in ["y", "ye", "yes"]:
                    prompts.remove(target_prompt)
                    prompt_storage.save_to_json(data_file, prompts)
                    print("\n[성공] 프롬프트가 삭제되었습니다.")
                    break
                else:
                    print("\n[알림] 삭제를 취소했습니다.")
            case "3":
                break
            case _:
                print("\n[경고] 잘못된 입력입니다. 1~3 사이의 번호를 선택해주세요.")
