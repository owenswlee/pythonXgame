######################載入套件######################

import pygame  # Import pygame for games
import sys  # Import system tools
import random  # Import random for platforms

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
        self.velocity_y = 0  # Vertical velocity
        self.jump_power = -12  # Jump velocity (negative is up)
        self.gravity = 0.5  # Gravity acceleration
        self.on_platform = False  # Whether on a platform

    def draw(self, display_area):
        """
        Draw the player \n
        display_area: Target drawing surface \n
        """
        pygame.draw.rect(display_area, self.color, self.rect)

    def move(self, direction, bg_x):
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

    def apply_gravity(self):
        """
        Apply gravity  \n
        Update vertical velocity and position  \n
        """
        self.velocity_y += self.gravity  # Add gravity
        self.rect.y += self.velocity_y  # Update vertical position

    def check_platform_collision(self, platforms):
        """
        Check platform collision  \n
        Platform to check  \n
        """
        # Check only when falling
        if self.velocity_y > 0:
            # Choose sample count for vertical speed
            check_points = max(1, int(abs(self.velocity_y) / 5))
            step_y = self.velocity_y / check_points

            for platform in platforms:
                for i in range(check_points):
                    test_rect = self.rect.copy()
                    test_rect.y += i * step_y

                    # Check platform contact
                    if (
                        test_rect.bottom >= platform.rect.top
                        and test_rect.bottom <= platform.rect.bottom
                        and test_rect.right > platform.rect.left
                        and test_rect.left < platform.rect.right
                    ):
                        self.rect.bottom = (
                            platform.rect.top
                        )  # Snap the player onto the platform
                        self.velocity_y = self.jump_power  # Set upward velocity
                        self.on_platform = True
                        return True
        return False


class Platform:
    def __init__(self, x, y, width, height, color):
        """
        Initialize the platform  \n
        x, y: Platform top-leftposition  \n
        width, height: Platform width and height  \n
        color: Platform color (RGB)  \n
        """
        self.rect = pygame.Rect(x, y, width, height)  # Create the platform rectangle
        self.color = color

    def draw(self, display_area):
        """
        Draw the platform  \n
        display_area: Target drawing surface  \n
        """
        pygame.draw.rect(display_area, self.color, self.rect)


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

###################### Platform Setup ######################

platform_w = 60  # Platform width
platform_h = 10  # platform height
platforms = []  # Create the platform list

# Create a base platform to catch the player

platform_x = (bg_x - platform_w)//2  # Center the platform
platform_y = bg_y - platform_h - 10  # Leave 10 pixels below

# Create a white platform

platform = Platform(platform_x, platform_y, platform_w, platform_h, (255, 255, 255))
platforms.append(platform)

# Generate extra platforms
platform_count = random.randint(8, 10) + 10  # Choose the extra count
for i in range(platform_count):
    x = random.randint(0, bg_x - platform_w)  # Choose platform x
    y = (bg_y - 100) - (i * 60)  # Space platform tops by 60 pixels
    platform = Platform(x, y, platform_w, platform_h, (255, 255, 255))
    platforms.append(platform)

###################### Custom Functions ######################
# Function that updates the camera

def update_camera():
    """
    Update the cameras and platforms  \n
    Above half height, keep the player in the middle of the screen  \n
    Move platforms so the player seems to climb  \n
    Remove platforms below the screen  \n
    Add new platforms above the screen  \n
    """
    screen_middle = bg_y // 2  # Screen middle y
    
    # If the player is above the midle, move the camera
    if player.rect.y < screen_middle:
        
        # Calculate how much to move the camera
        camera_move = screen_middle - player.rect.y
        player.rect.y = screen_middle  # Keep the player in the middle

        # Move all platform
        for platform in platforms:
            platform.rect.y += camera_move  

        # Remove platforms that are below the screen
        y_min = bg_y 
        for platform in platforms:
            if platform.rect.top > bg_y:
                platforms.remove(platform)  # Remove the platform
            if platform.rect.top < y_min:
                y_min = platform.rect.top  # Update the minimum y

        # Add new platforms on top
        if len(platforms) < platform_count:
            x = random.randint(0, bg_x - platform_w)  # Choose platform x
            y = y_min - 60  # Space platform tops by 60 pixels
            platform = Platform(x, y, platform_w, platform_h, (255, 255, 255))
            platforms.append(platform)

######################主程式######################

while True:
    FPS.tick(60)  # Cap framerate at 60
    screen.fill((0, 0, 0))  # Clear to black

    update_camera()  # Update the camera and platforms

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:  # While Left is held
        player.move(-1, bg_x)
    if keys[pygame.K_RIGHT]:  # While Right is held
        player.move(1, bg_x)

    # Apply gravity and check collision
    player.apply_gravity()
    player.check_platform_collision(platforms)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # On window close
            sys.exit()  # Exit

    # Draw all platforms
    for platform in platforms:
        platform.draw(screen)  # Draw the platform

    player.draw(screen)  # Draw the player
    pygame.display.update()  # Update the display
