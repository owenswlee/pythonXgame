
######################載入套件/ import packages######################

import pygame
import sys
import random

######################物件類別/ object class######################

class Brick:
    def __init__(self, x, y, width, height, color):
        """
        Initiaize the brick \n
        x, y: / Top left coordinates \n
        width, height: / Width and height \n
        color: / Brick color \n
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.hit = False

    def draw(self, display_area):
        """
        Draw the brick \n
        screen: / The screen to draw on \n
        """
        if not self.hit:
            pygame.draw.rect(display_area, self.color, self.rect)

######################定義函式區/ define functions######################

######################初始化設定/ initialize settings######################

# Initialize once
pygame.init()  # start pygame
FPS = pygame.time.Clock()  # Set FPS

######################載入圖片/ load images######################

######################遊戲視窗設定/ game window settings######################

bg_x = 800
bg_y = 600
bg_size = (bg_x, bg_y)
bg = pygame.display.set_caption("Brick Game")
screen = pygame.display.set_mode(bg_size)

######################磚塊設定/ brick settings######################

bricks_row = 9
bricks_col = 11
brick_w = 58
brick_h = 16
bricks_gap = 2
bricks = []  # List of brick objects
for col in range(bricks_col):
    for row in range(bricks_row):
            x = col * (brick_w + bricks_gap) + 70  # Start X = 70
            y = row * (brick_h + bricks_gap) + 60  # Start Y = 60
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            brick = Brick(x, y, brick_w, brick_h, color)
            bricks.append(brick)

######################顯示文字設定/ text display settings######################

######################底板設定/ paddle settings######################

pad = Brick(0, bg_y - 48, brick_w, brick_h, (255, 255, 255))  # Create the paddle

######################球設定/ ball settings######################

######################遊戲結束設定/ game over settings######################

######################主程式/ main program######################

while True:
    FPS.tick(1000)  # 60 FPS
    screen.fill((0, 0, 0))  # Clear the screen
    mos_x, mos_y = pygame.mouse.get_pos()  # Get mouse position
    pad.rect.x = mos_x - pad.rect.width // 2  # Center the paddle on the mouse

    if pad.rect.x < 0:  # Keeping inside the left edge
        pad.rect.x = 0

    if pad.rect.x + pad.rect.width > bg_x:  # Keeping inside the right edge
        pad.rect.x = bg_x - pad.rect.width

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    for brick in bricks:
        brick.draw(screen)

    pad.draw(screen)

    pygame.display.update() 