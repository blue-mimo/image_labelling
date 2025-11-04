from PIL import Image, ImageDraw
import io

# Create 32x32 favicon
img = Image.new('RGB', (32, 32), '#007cba')
draw = ImageDraw.Draw(img)

# Draw image frame (white rectangle)
draw.rectangle([4, 4, 28, 28], fill='white', outline='#007cba', width=1)

# Draw image content (circle representing photo)
draw.ellipse([8, 8, 16, 16], fill='#007cba')

# Draw label lines
draw.rectangle([18, 8, 26, 10], fill='#007cba')
draw.rectangle([18, 12, 24, 14], fill='#007cba')
draw.rectangle([18, 16, 22, 18], fill='#007cba')

# Save as ICO
img.save('favicon.ico', format='ICO', sizes=[(32, 32)])
print("Favicon created successfully!")