import os

import prompt_storage


# 현재 프롬프트 목록을 Markdown 파일로 내보내는 메뉴 함수입니다.
def export_markdown_menu(prompts, export_file):
    """프롬프트를 카테고리별로 분류하여 Markdown 파일로 내보냅니다."""
    if not prompts:
        print("\n[안내] 등록된 프롬프트가 없어 내보낼 수 없습니다.")
        return

    print("\n=== Markdown 내보내기 ===")
    default_name = "prompts.md"
    file_input = input(f"내보낼 파일명 입력 (기본값: {default_name}): ").strip()

    if not file_input:
        filepath = export_file
        filename = default_name
    else:
        if not file_input.endswith(".md"):
            file_input += ".md"
        filepath = os.path.join(os.path.dirname(export_file), file_input)
        filename = file_input

    print(f"\n[알림] 프롬프트 보관함을 '{filename}' 파일로 내보내는 중...")
    success = prompt_storage.export_to_markdown(filepath, prompts)

    if success:
        print(f"[성공] 파일 내보내기가 완료되었습니다. 경로: {filepath}")
    else:
        print("[오류] 파일 내보내기에 실패했습니다.")
