import prompt_storage
from prompt_actions import print_prompt_summary, select_prompt_by_number


# 선택한 프롬프트의 즐겨찾기 상태를 등록 또는 해제하는 함수입니다.
def toggle_favorite(prompts, data_file):
    """특정 프롬프트의 즐겨찾기 설정을 해제하거나 추가합니다 (토글)."""
    target_prompt = select_prompt_by_number(prompts, "즐겨찾기 관리 (토글)", "즐겨찾기 상태를 변경할 프롬프트")
    if not target_prompt:
        return

    # 토글 처리
    target_prompt["favorite"] = not target_prompt.get("favorite", False)
    prompt_storage.save_to_json(data_file, prompts)
    status_str = "등록" if target_prompt["favorite"] else "해제"
    print(f"\n[성공] '{target_prompt.get('title')}' 프롬프트가 즐겨찾기에 {status_str}되었습니다.")


# 즐겨찾기로 등록된 프롬프트만 모아 목록으로 출력하는 함수입니다.
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
        print_prompt_summary(idx, p)

    print(f"\n총 {len(favorites)}개의 즐겨찾기 프롬프트")
