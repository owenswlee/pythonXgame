
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
class Ball:
    def __init__(self, x, y, radius, color):
        """
        Initiaize the ball \n
        x, y:Ball center coordinates \n
        radius: / Ball radius \n
        color: / Ball color \n
        """
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.speed_x = 5  # Initial horizontal speed
        self.speed_y = 5  # Initial vertical speed (negative)
        self.is_moving = False  # Whether the ball is moving
    def draw(self, display_area):
        """
        Draw the ball \n
        display_area: / Drawing area \n
        """
        pygame.draw.circle(display_area, self.color, (int(self.x), int(self.y)), self.radius)
    def move(self):
        """
        Move the ball 
        """
        if self.is_moving:
            self.x += self.speed_x
            self.y += self.speed_y

    def check_collision(self, bg_x, bg_y, bricks, pad):
        
        """
        Check collisions and bounce \n
        bg_x, bg_y: Window width and height \n
        bricks: Brick list \n
        pad: Paddle object
        """
        # Check window edges
        if self.x - self.radius <= 0 or self.x + self.radius >= bg_x:
            self.speed_x = -self.speed_x  # Horizontal bounce

        if self.y - self.radius <= 0:
            self.speed_y = -self.speed_y  # Vertical bounce

        # Check if the ball falls below window (game over)
        if self.y + self.radius > bg_y:
            self.is_moving = False  # Stop the ball 

        # Check the paddle
        if (
            self.y + self.radius >= pad.rect.y
            and self.y + self.radius <= pad.rect.y + pad.rect.height
            and self.x >= pad.rect.x
            and self.x <= pad.rect.x + pad.rect.width
        ):
            self.speed_y = -abs(self.speed_y)  # Bounce upward

        # Check the bricks
        for brick in bricks:
            if not brick.hit:  # Check only unhit bricks
                # Simple collision check
                # Find distances between centers 
                dx = abs(self.x - (brick.rect.x + brick.rect.width // 2))
                dy = abs(self.y - (brick.rect.y + brick.rect.height // 2))

                # Check for a collision
                if dx <= (self.radius + brick.rect.width / 2) and dy <= (self.radius + brick.rect.height / 2):
                    brick.hit = True  # Mark the brick as hit

                    # Choose the bounce direction
                    # Use te side contact
                    if self.x < brick.rect.x or self.x > brick.rect.x + brick.rect.width:
                        self.speed_x = -self.speed_x
                    else:
                        self.speed_y = -self.speed_y

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

ball_radius = 10
ball_color = (255, 215, 0)  # gold
ball = Ball(pad.rect.x + pad.rect.width // 2, pad.rect.y - ball_radius, ball_radius, ball_color)

######################遊戲結束設定/ game over settings######################

######################主程式/ main program######################

while True:
    FPS.tick(60) # set fps
    screen.fill((0, 0, 0))  # Clear the screen
    mos_x, mos_y = pygame.mouse.get_pos()  # Get mouse position
    pad.rect.x = mos_x - pad.rect.width // 2  # Center the paddle on the mouse

    if pad.rect.x < 0:  # Keeping inside the left edge
        pad.rect.x = 0

    if pad.rect.x + pad.rect.width > bg_x:  # Keeping inside the right edge
        pad.rect.x = bg_x - pad.rect.width

    # Follow the paddle when stopped
    if not ball.is_moving:
        ball.x = pad.rect.x + pad.rect.width // 2
        ball.y = pad.rect.y - ball_radius
    else:
        # Move and check collisions
        ball.move()
        ball.check_collision(bg_x, bg_y, bricks, pad)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Click to launch the ball
            if not ball.is_moving:
                ball.is_moving = True

    for brick in bricks:
        brick.draw(screen)

    pad.draw(screen)
    ball.draw(screen)  # Draw the ball

    pygame.display.update() 