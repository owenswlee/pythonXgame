######################載入套件######################

import pygame  # Import pygame for games
import sys  # Import system tools

######################物件類別######################

class Player: 
    def __init__(self, x, y, width, height, color):
        """
        Initialize the player \n
        Top left position \n
        Player width and height \n
        Player color (RGB) \n
        """
        self.rect = pygame.Rect(x, y, width, height)  # Create the player rectangle
        self.color = color
        self.speed = 5  # Movement speed
    def draw(self, display_area):
        """
        Draw the player \n
        display_area: Target drawing surface \n
        """
        pygame.draw.rect(display_area, self.color, self.rect)
    def move (self, direction, bg_x):
        """
        Move and wrap the player \n
        direction: Direction (1 right, -1 left) \n
        bg_x: Window width for wrapping \n
        """
        self.rect.x += direction * self.speed
        # Wrap around the screen 
        if self.rect.right < 0:  # Fully past the left edge
            self.rect.left = bg_x  # Reappear at the right
        elif self.rect.left > bg_x:  # Fully past the right edge
            self.rect.right = 0  # Reappear at the left
            
        
######################初始化設定######################

pygame.init()  # Initialize pygame
FPS = pygame.time.Clock()  # Create the frame clock

######################遊戲視窗設定######################

bg_x = 400  # Window width
bg_y = 600  # Window height
bg_size = (bg_x, bg_y)  # Window size tuple
pygame.display.set_caption("Doodle Jump")  # Window title
screen = pygame.display.set_mode(bg_size)  # Create the window

######################主角設定######################

player_w = 30  # player width
player_h = 30  # player height
player_x = (bg_x - player_w) // 2
player_y = bg_y - player_h - 50
# Create a green player
player = Player(player_x, player_y, player_w, player_h, (0, 255, 0))

######################主程式######################

while True:
    FPS.tick(60)  # Cap framerate at 60
    screen.fill((0, 0, 0))  # Clear to black

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:  # While Left is held
        player.move(-1, bg_x)
    if keys[pygame.K_RIGHT]:  # While Right is held
        player.move(1, bg_x)
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # On window close
            sys.exit()  # Exit
    player.draw(screen)  # Draw the player
    pygame.display.update()  # Update the display

