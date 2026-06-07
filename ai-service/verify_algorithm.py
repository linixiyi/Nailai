import asyncio
from pathlib import Path
from app.services.nail_core_algorithm import analyze_style_length, generate_joint_mask, execute_commercial_try_on

def get_test_images():
    base_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "style-images"
    user_img = base_dir / "group-20260514-212714" / "1.png"
    style_img = base_dir / "library-20260514" / "library-20260514-003.png"
    return user_img, style_img

async def test():
    user_img, style_img = get_test_images()
    
    with open(user_img, "rb") as f:
        user_bytes = f.read()
    with open(style_img, "rb") as f:
        style_bytes = f.read()
        
    print("Testing Pipeline A (analyze_style_length)...")
    level = analyze_style_length(style_bytes)
    print(f"Style level detected: {level}")
    
    print("Testing Pipeline B (generate_joint_mask)...")
    mask_bytes = generate_joint_mask(user_bytes, level)
    with open("test_mask_output.png", "wb") as f:
        f.write(mask_bytes)
    print("Mask saved to test_mask_output.png")
    
    print("Testing Pipeline D (DashScope Generation)...")
    url = await execute_commercial_try_on(user_bytes, style_bytes)
    print(f"Result URL: {url}")

if __name__ == "__main__":
    asyncio.run(test())
