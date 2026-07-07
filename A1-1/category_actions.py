from prompt_actions import get_category_options, print_prompt_summary


# 선택한 카테고리에 해당하는 프롬프트만 필터링하여 출력하는 함수입니다.
def show_category_prompts(prompts):
    """카테고리별로 프롬프트를 필터링하여 조회합니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없습니다.")
        return

    category_options = get_category_options(prompts)

    if not category_options:
        print("\n[안내] 카테고리 정보가 없습니다.")
        return

    print("\n=== 카테고리별 조회 ===")
    for idx, cat in enumerate(category_options, 1):
        print(f"{idx}. {cat}")

    while True:
        choice = input("조회할 카테고리 번호: ").strip()
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(category_options):
                selected_cat = category_options[choice_idx]
                break
            else:
                print("[경고] 올바른 범위의 번호를 입력해주세요.")
        except ValueError:
            print("[경고] 숫자를 입력해주세요.")

    filtered = [p for p in prompts if p.get("category") == selected_cat]

    print(f"\n=== 카테고리 [{selected_cat}] 조회 결과 ===")
    if not filtered:
        print("[안내] 해당 카테고리에 등록된 프롬프트가 없습니다.")
        print("\n총 0개의 프롬프트")
        return

    for idx, p in enumerate(filtered, 1):
        print_prompt_summary(idx, p)

    print(f"\n총 {len(filtered)}개의 프롬프트")
