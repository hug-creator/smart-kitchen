"""把多张截图合成为演示 GIF。"""

from pathlib import Path

from PIL import Image

SHOTS_DIR = Path(r"D:\219\smart-kitchen\docs\demo_shots")
OUT = Path(r"D:\219\smart-kitchen\docs\demo.gif")


def main():
    files = sorted(SHOTS_DIR.glob("*.png"))
    images = [Image.open(f) for f in files]

    # 帧时长（ms）：首页2秒 → 点餐1秒 → 结果3秒 → 库存2秒 → 历史2秒 → 监控2秒
    durations = [2000, 1000, 3000, 2000, 2000, 2500]

    images[0].save(
        OUT,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,           # 无限循环
        optimize=True,
    )

    size_kb = OUT.stat().st_size // 1024
    print(f"GIF 已生成：{OUT}  ({size_kb} KB,  {len(files)} 帧)")


if __name__ == "__main__":
    main()