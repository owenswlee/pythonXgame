######################匯入模組######################
import pygame
import sys
######################初始化######################
pygame.init()  # start pygame
width = 640  # screen width
height = 320  # screen height
######################建立視窗及物件######################
# screen size
screen = pygame.display.set_mode((width, height))
# screen title
pygame.display.set_caption("Python Game")
######################建立畫布######################
# create a background
bg = pygame.Surface((width, height))
# fill the background with blue
bg.fill((255, 255, 255))
######################繪製圖型######################
# draw a circle, (backgroung, color, x, y, radius, width)
pygame.draw.circle(bg, (0, 0, 0), (200, 100), 30, 0)
pygame.draw.circle(bg, (0, 0, 0), (400, 100), 30, 0)

# draw a rectangle, (backgroung, color,[x, y, width, height], width)
pygame.draw.rect(bg, (0, 255, 0), [270, 130, 60, 40 ], 5)

# draw a oval, (background, color, [x, y, width, height], width)
pygame.draw.ellipse(bg, (0, 0, 255), [130, 160, 60, 35 ], 5)
pygame.draw.ellipse(bg, (0, 0, 255), [400, 160, 60, 35 ], 5)

# draw a line, (background, color, start, end, width)
pygame.draw.line(bg, (255, 0, 255), (280, 220), (320, 220), 3)
######################循環偵測######################
ispen = False
while True:
    x, y = pygame.mouse.get_pos()  # get mouse position
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # user clicked close button
            sys.exit()  # exit the game

        if event.type == pygame.MOUSEBUTTONDOWN:

            print(f"Mouse button pressed at {x}, {y}")
            pygame.draw.circle(bg, (0, 0, 0), (x, y), 30, 0)
            ispen = not (ispen)  # toggle pen state
            print(f"ispen: {ispen}")

    if ispen:
        pygame.draw.circle(bg, (0, 0, 0), (x, y), 30, 0)  # draw pen

    # draw the background starting from top-left corner
    screen.blit(bg, (0, 0))  # draw canvas on window top-left corner
    # reload screen
    pygame.display.update()  # update window