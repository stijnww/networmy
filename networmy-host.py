# Wormy (a Nibbles clone)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license

import random, pygame, sys
from pygame.locals import *
import socket
import threading
import json
import logging
import re

FPS = 10
WINDOWWIDTH = 1600
WINDOWHEIGHT = 900
CELLSIZE = 20
assert WINDOWWIDTH % CELLSIZE == 0, "Window width must be a multiple of cell size."
assert WINDOWHEIGHT % CELLSIZE == 0, "Window height must be a multiple of cell size."
CELLWIDTH = int(WINDOWWIDTH / CELLSIZE)
CELLHEIGHT = int(WINDOWHEIGHT / CELLSIZE)

#               R    G    Be
WHITE       = (255, 255, 255)
BLACK       = (  0,   0,   0)
DARKGRAY    = ( 40,  40,  40)
DARKGREEN   = (  0, 155,   0)

# WORM COLORS FOR MULTIPLAYER
RED         = (255,   0,   0)
INNERRED    = (139,   0,   0)
GREEN       = (  0, 255,   0)
INNERGREEN  = (  0, 139,   0)
ORANGE      = (255, 165,   0)
INNERORANGE = (255, 140,   0)
YELLOW      = (255, 255,   0)
INNERYELLOW = (200, 200,   0)
PURPLE      = (128,   0, 128)
INNERPURPLE = ( 75,   0, 130)
CYAN        = (  0, 255, 255)
INNERCYAN   = (  0, 139, 139)
PINK        = (255, 192, 203)
INNERPINK   = (199,  21, 133)
BLUE        = (  0,   0, 255)
INNERBLUE   = (  0,   0, 139)

wormColors = [GREEN, RED, ORANGE, YELLOW, PURPLE, CYAN, PINK, BLUE]

BGCOLOR = BLACK

UP      = 0
DOWN    = 1
LEFT    = 2
RIGHT   = 3

HEAD    = 0 # syntactic sugar: index of the worm's head

game_started = False

clients = []
snakes = []
client_ips = {}
inputQueue = []
global socketConnection

def main():
    global FPSCLOCK, DISPLAYSURF, BASICFONT, game_started, socketConnection

    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
    pygame.display.set_caption('Wormy')

    game_code = get_local_ip()
    socketConnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_thread = threading.Thread(target=start_server)
    server_thread.start()  # Start the server in a separate thread
    showHostPauseScreen(game_code)

def runGame(conn, snake_id):
    global snakes, clients
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()

        # Update snake positions every frame
        update_snake_positions()

        # Send game update to all clients
        game_update = {
            'type': 'board_update',
            'snakes': [
                {
                    'coords': [[coord['x'], coord['y']] for coord in snake['coords']],
                    'color': snake['color'],
                    'direction': snake['direction']
                } for snake in snakes
            ]
        }
        for client in clients:
            try:
                client.sendall(json.dumps(game_update).encode())
                logging.info(f"Sent game update to client {clients.index(client)}")
                logging.info(f"Game update: {game_update}")
            except Exception as e:
                logging.error(f"Error sending data to client: {e}")
                clients.remove(client)
                client.close()

        DISPLAYSURF.fill(BGCOLOR)
        drawGrid()
        for snake in snakes:
            drawWorm(snake['coords'], snake['color'])
        pygame.display.update()
        FPSCLOCK.tick(FPS)

def send_move(conn, snake_id, move):
    move_data = {'id': snake_id, 'move': move}
    conn.sendall(json.dumps(move_data).encode())
    logging.info(f"Sent move to client {snake_id}")
    logging.info(f"Move data: {move_data}")

def drawPressKeyMsg():
    pressKeySurf = BASICFONT.render('Press a key to play.', True, DARKGRAY)
    pressKeyRect = pressKeySurf.get_rect()
    pressKeyRect.topleft = (WINDOWWIDTH - 200, WINDOWHEIGHT - 30)
    DISPLAYSURF.blit(pressKeySurf, pressKeyRect)

def checkForKeyPress():
    keyUpEvents = pygame.event.get(KEYUP)
    if len(keyUpEvents) == 0:
        return None
    print(f"Key released: {keyUpEvents[0].key}")  # Print for debugging
    if keyUpEvents[0].key == K_ESCAPE:
        terminate()
    return keyUpEvents[0].key


def showStartScreen():
    titleFont = pygame.font.Font('freesansbold.ttf', 100)
    titleSurf1 = titleFont.render('Wormy!', True, WHITE, DARKGREEN)
    titleSurf2 = titleFont.render('Wormy!', True, GREEN)

    degrees1 = 0
    degrees2 = 0
    while True:
        DISPLAYSURF.fill(BGCOLOR)
        rotatedSurf1 = pygame.transform.rotate(titleSurf1, degrees1)
        rotatedRect1 = rotatedSurf1.get_rect()
        rotatedRect1.center = (WINDOWWIDTH / 2, WINDOWHEIGHT / 2)
        DISPLAYSURF.blit(rotatedSurf1, rotatedRect1)

        rotatedSurf2 = pygame.transform.rotate(titleSurf2, degrees2)
        rotatedRect2 = rotatedSurf2.get_rect()
        rotatedRect2.center = (WINDOWWIDTH / 2, WINDOWHEIGHT / 2)
        DISPLAYSURF.blit(rotatedSurf2, rotatedRect2)

        drawPressKeyMsg()

        if checkForKeyPress():
            pygame.event.get()  # clear event queue
            return
        pygame.display.update()
        FPSCLOCK.tick(FPS)
        degrees1 += 3  # rotate by 3 degrees each frame
        degrees2 += 7  # rotate by 7 degrees each frame

def showHostPauseScreen(game_code):
    global clients, game_started
    titleFont = pygame.font.Font('freesansbold.ttf', 50)
    titleSurf = titleFont.render('Game Code: ' + game_code, True, WHITE)
    titleRect = titleSurf.get_rect()
    titleRect.center = (WINDOWWIDTH / 2, WINDOWHEIGHT / 4)

    startButton = pygame.Rect(WINDOWWIDTH / 2 - 75, WINDOWHEIGHT / 2, 150, 50)

    while True:
        DISPLAYSURF.fill(BGCOLOR)
        DISPLAYSURF.blit(titleSurf, titleRect)

        pygame.draw.rect(DISPLAYSURF, GREEN, startButton)
        startText = BASICFONT.render('Start', True, WHITE)
        startTextRect = startText.get_rect(center=startButton.center)
        DISPLAYSURF.blit(startText, startTextRect)

        noClientSurf = BASICFONT.render('At least one client is required to start the game.', True, RED)
        noClientRect = noClientSurf.get_rect(center=(WINDOWWIDTH / 2, WINDOWHEIGHT / 2 + 100))
        DISPLAYSURF.blit(noClientSurf, noClientRect)

        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type == MOUSEBUTTONUP:
                mouseX, mouseY = event.pos
                if startButton.collidepoint((mouseX, mouseY)):
                    if len(clients) > 0:  # Check if at least one client is connected
                        # Define start positions for each side of the screen
                        start_positions = [
                            [(5, 5), (5, 6), (5, 7)],  # Top-left
                            [(5, 20), (5, 21), (5, 22)],  # middle-left
                            [(5, 40), (5, 21), (5, 22)],  # Bottom-left
                        ]

                        # Send start message to all clients
                        for i, client in enumerate(clients):
                            print(f"Sending start message to client {i}")
                            snake_coords = [{'x': x, 'y': y} for x, y in start_positions[i % len(start_positions)]]
                            snake_color = wormColors[i % len(wormColors)]
                            start_message = json.dumps({
                                "type": "start",
                                "coords": {
                                    "coords": [[coord['x'], coord['y']] for coord in snake_coords],
                                    "color": snake_color
                                }
                            }).encode()
                            client.sendall(start_message)
                            print(f"Sent start message to client {i}")
                            snakes.append({'id': i, 'coords': snake_coords, 'direction': RIGHT, 'color': snake_color})
                        game_started = True  # Set game_started to True for the host
                        runGame(clients[0], 0)  # Start the game and pass the first client connection and snake_id
                        return
                    else:
                        print("No clients connected")

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def get_local_ip():
    tempSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        tempSocket.connect(('10.254.254.254', 1))
        ip = tempSocket.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        tempSocket.close()
    return ip


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_client(conn, addr):
    global clients, snakes, client_ips, inputQueue
    ip = addr[0]
    logging.info(f"Connected by {addr}")

    if ip in client_ips:
        client_ips[ip] += 1
    else:
        client_ips[ip] = 1

    if client_ips[ip] > 5:  # Limit to 5 connections per IP
        logging.warning(f"Too many connections from {ip}. Closing connection.")
        conn.close()
        return

    clients.append(conn)
    snake_id = len(snakes)
    snake_color = wormColors[snake_id % len(wormColors)]
    try:
        with conn:
            buffer = ""
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break

                buffer += data
                json_objects = re.findall(r'\{.*?\}(?=\{)|\{.*?\}$', buffer)
                buffer = re.sub(r'\{.*?\}(?=\{)|\{.*?\}$', '', buffer)
                logging.info(f"Received JSON objects: {json_objects}")
                # log how many json objects were received
                logging.info(f"Received {len(json_objects)} JSON objects")

                for msgData in json_objects:
                    try:
                        msgData = json.loads(msgData)
                        if msgData["type"] == 'direction':
                            direction = int(msgData["direction"])
                            if direction in [UP, DOWN, LEFT, RIGHT]:
                                # add direction to input queue
                                inputQueue.append((snake_id, direction))
                                logging.info(f"Added direction to input queue: {direction}")
                    # exception with JSON parsing
                    except Exception as e:
                        logging.error(f"Error: {e}")
    # exception with connection
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        clients.remove(conn)
        client_ips[ip] -= 1
        if client_ips[ip] == 0:
            del client_ips[ip]
        logging.info(f"Disconnected by {addr}")

def start_server():
    HOST = get_local_ip()
    PORT = 65432
    print(f"Server IP: {HOST}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serverSocket:
        serverSocket.bind((HOST, PORT))
        serverSocket.listen()
        print(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = serverSocket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

def direction_to_constant(direction):
    if direction == 0:
        return UP
    elif direction == 1:
        return DOWN
    elif direction == 2:
        return LEFT
    elif direction == 3:
        return RIGHT


def update_snake_positions():
    global snakes, inputQueue
    for snake in snakes[:]:  # Iterate over a copy of the list to allow removal
        # Check for input queue
        if len(inputQueue) > 0:
            # Check if the input is for this snake
            snake_id, direction = inputQueue.pop(0)
            if snake_id == snake['id']:
                # check if the move is valid
                if snake['direction'] == UP and direction == DOWN:
                    continue
                elif snake['direction'] == DOWN and direction == UP:
                    continue
                elif snake['direction'] == LEFT and direction == RIGHT:
                    continue
                elif snake['direction'] == RIGHT and direction == LEFT:
                    continue
                snake['direction'] = direction_to_constant(direction)


        newHead = calculate_new_position(snake['coords'][HEAD], snake['direction'])

        # Check for collision with boundaries
        if newHead['x'] < 0 or newHead['x'] >= CELLWIDTH or newHead['y'] < 0 or newHead['y'] >= CELLHEIGHT:
            print(f"Snake {snake['id']} collided with the boundary and will be removed.")
            snakes.remove(snake)
            continue

        # Check for collision with itself
        if newHead in snake['coords']:
            print(f"Snake {snake['id']} collided with itself and will be removed.")
            snakes.remove(snake)
            continue

        snake['coords'].insert(0, newHead)
        snake['coords'].pop()

def calculate_new_position(head, direction):
    if direction == UP:
        return {'x': head['x'], 'y': head['y'] - 1}
    elif direction == DOWN:
        return {'x': head['x'], 'y': head['y'] + 1}
    elif direction == LEFT:
        return {'x': head['x'] - 1, 'y': head['y']}
    elif direction == RIGHT:
        return {'x': head['x'] + 1, 'y': head['y']}

def terminate():
    pygame.quit()
    sys.exit()

def getRandomLocation():
    return {'x': random.randint(0, CELLWIDTH - 1), 'y': random.randint(0, CELLHEIGHT - 1)}

def showGameOverScreen():
    gameOverFont = pygame.font.Font('freesansbold.ttf', 150)
    gameSurf = gameOverFont.render('Game', True, WHITE)
    overSurf = gameOverFont.render('Over', True, WHITE)
    gameRect = gameSurf.get_rect()
    overRect = overSurf.get_rect()
    gameRect.midtop = (WINDOWWIDTH / 2, 10)
    overRect.midtop = (WINDOWWIDTH / 2, gameRect.height + 10 + 25)

    DISPLAYSURF.blit(gameSurf, gameRect)
    DISPLAYSURF.blit(overSurf, overRect)
    drawPressKeyMsg()
    pygame.display.update()
    pygame.time.wait(500)
    checkForKeyPress()  # clear out any key presses in the event queue

    while True:
        if checkForKeyPress():
            pygame.event.get()  # clear event queue
            return

def drawScore(score):
    scoreSurf = BASICFONT.render('Score: %s' % (score), True, WHITE)
    scoreRect = scoreSurf.get_rect()
    scoreRect.topleft = (WINDOWWIDTH - 120, 10)
    DISPLAYSURF.blit(scoreSurf, scoreRect)

def drawWorm(wormCoords, wormColor=GREEN):
    for coord in wormCoords:
        x = coord['x'] * CELLSIZE
        y = coord['y'] * CELLSIZE
        wormSegmentRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
        pygame.draw.rect(DISPLAYSURF, wormColor, wormSegmentRect)
        wormInnerSegmentRect = pygame.Rect(x + 4, y + 4, CELLSIZE - 8, CELLSIZE - 8)
        pygame.draw.rect(DISPLAYSURF, getInnerColor(wormColor), wormInnerSegmentRect)

def getInnerColor(wormColor):
    if wormColor == GREEN:
        return INNERGREEN
    elif wormColor == RED:
        return INNERRED
    elif wormColor == ORANGE:
        return INNERORANGE
    elif wormColor == YELLOW:
        return INNERYELLOW
    elif wormColor == PURPLE:
        return INNERPURPLE
    elif wormColor == CYAN:
        return INNERCYAN
    elif wormColor == PINK:
        return INNERPINK
    elif wormColor == BLUE:
        return INNERBLUE
    else:  # default to GREEN
        return INNERGREEN

def drawApple(coord):
    x = coord['x'] * CELLSIZE
    y = coord['y'] * CELLSIZE
    appleRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
    pygame.draw.rect(DISPLAYSURF, RED, appleRect)

def drawGrid():
    for x in range(0, WINDOWWIDTH, CELLSIZE):  # draw vertical lines
        pygame.draw.line(DISPLAYSURF, DARKGRAY, (x, 0), (x, WINDOWHEIGHT))
    for y in range(0, WINDOWHEIGHT, CELLSIZE):  # draw horizontal lines
        pygame.draw.line(DISPLAYSURF, DARKGRAY, (0, y), (WINDOWWIDTH, y))

if __name__ == '__main__':
    main()