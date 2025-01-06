# Wormy (a Nibbles clone
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license
import socket
import random
import pygame
import sys
from pygame.locals import *
import json
import threading
import queue
from time import sleep

HOST = "10.157.0.60"
PORT = 65432

FPS = 128
WINDOWWIDTH = 1600
WINDOWHEIGHT = 900
CELLSIZE = 20
assert WINDOWWIDTH % CELLSIZE == 0, "Window width must be a multiple of cell size."
assert WINDOWHEIGHT % CELLSIZE == 0, "Window height must be a multiple of cell size."
CELLWIDTH = int(WINDOWWIDTH / CELLSIZE)
CELLHEIGHT = int(WINDOWHEIGHT / CELLSIZE)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.settimeout(1.0)
print(f"Connection established with {HOST}:{PORT}")

#             R    G    B
WHITE     = (255, 255, 255)
BLACK     = (  0,   0,   0)
RED       = (255,   0,   0)
GREEN     = (  0, 255,   0)
DARKGREEN = (  0, 155,   0)
DARKGRAY  = ( 40,  40,  40)
BGCOLOR = BLACK

UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3

HEAD = 0 # syntactic sugar: index of the worm's head
direction = RIGHT

def main():
    global FPSCLOCK, DISPLAYSURF, BASICFONT

    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
    pygame.display.set_caption('Wormy')

    waitForStart()
    runGame()

def runGame():
    snakes = []
    running = True

    def receive_updates():
        while running:
            FPSCLOCK.tick(FPS)

            print("Receiving updates")
            try:
                buffer = ''
                while True:
                    data = s.recv(1024)
                    if not data:
                        print("No data")
                        continue
                    buffer += data.decode()
                    while '\n' in buffer:
                        message, buffer = buffer.split('\n', 1)
                        message = json.loads(message)
                        print(f"Received message: {message}")
                        if message['type'] == 'board_update':
                            snakes = message['snakes']
                            print(snakes)
                            # drawApple(snake['apple'])
                            # drawScore(snake['score'])
                            drawGrid()
                            for snake in json.loads(str(snakes)):
                                drawWorm(snake['coords'], snake['color'])
            except socket.timeout:
                print("Timeout")
                continue
            except Exception as e:
                print(f"Error while receivingd: {e}")
                break
    receive_thread = threading.Thread(target=receive_updates)
    receive_thread.start()

    print("Sending direction")
    inputQueue = []
    while running:
        FPSCLOCK.tick(FPS)
        for event in pygame.event.get():
            if event.type == QUIT:
                s.sendall(json.dumps({'type': 'quit'}).encode())
                print("Sent quit message")
                terminate()
            elif event.type == KEYDOWN:
                if event.key == K_w:
                    direction = UP
                elif event.key == K_a:
                    direction = LEFT
                elif event.key == K_s:
                    direction = DOWN
                elif event.key == K_d:
                    direction = RIGHT
                elif event.key == K_ESCAPE:
                    s.sendall(json.dumps({'type': 'quit'}).encode())
                s.sendall((json.dumps({'type': 'direction', 'direction': direction})).encode())
                print(f"Sent direction: {json.dumps({'type': 'direction', 'direction': direction})}")
            else:
                continue
    
    
    receive_thread.join()

def updateBoard(snake):
    for segment in snake:
        wormCoords = segment['coords']
        drawWorm(wormCoords)
    pygame.display.update()
    FPSCLOCK.tick(FPS)

def drawWorm(wormCoords, color):
    for coord in wormCoords:
        x = coord['x'] * CELLSIZE
        y = coord['y'] * CELLSIZE
        wormSegmentRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
        pygame.draw.rect(DISPLAYSURF, DARKGREEN, wormSegmentRect)
        wormInnerSegmentRect = pygame.Rect(x + 4, y + 4, CELLSIZE - 8, CELLSIZE - 8)
        pygame.draw.rect(DISPLAYSURF, GREEN, wormInnerSegmentRect)
    pygame.display.update()
    FPSCLOCK.tick(FPS)

def terminate():
    pygame.quit()
    exit()

def drawPressKeyMsg():
    pressKeySurf = BASICFONT.render('Press a key to play.', True, DARKGRAY)
    pressKeyRect = pressKeySurf.get_rect()
    pressKeyRect.topleft = (WINDOWWIDTH - 200, WINDOWHEIGHT - 30)
    DISPLAYSURF.blit(pressKeySurf, pressKeyRect)


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

        if waitForStart():
            pygame.event.get() # clear event queue
            return
        pygame.display.update()
        FPSCLOCK.tick(FPS)
        degrees1 += 3 # rotate by 3 degrees each frame
        degrees2 += 7 # rotate by 7 degrees each frame

def waitForStart():
    while True:
        try:
            data = s.recv(1024)
            if not data:
                continue
            message = json.loads(data.decode())
            if message['type'] == 'start':
                print("Game starting")
                return
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break


# def showGameOverScreen():
#     gameOverFont = pygame.font.Font('freesansbold.ttf', 150)
#     gameSurf = gameOverFont.render('Game', True, WHITE)
#     overSurf = gameOverFont.render('Over', True, WHITE)
#     gameRect = gameSurf.get_rect()
#     overRect = overSurf.get_rect()
#     gameRect.midtop = (WINDOWWIDTH / 2, 10)
#     overRect.midtop = (WINDOWWIDTH / 2, gameRect.height + 10 + 25)

#     DISPLAYSURF.blit(gameSurf, gameRect)
#     DISPLAYSURF.blit(overSurf, overRect)
#     drawPressKeyMsg()
#     pygame.display.update()
#     pygame.time.wait(500)
#     checkForKeyPress() # clear out any key presses in the event queue

#     while True:
#         if checkForKeyPress():
#             pygame.event.get() # clear event queue
#             return

def drawScore(score):
    scoreSurf = BASICFONT.render('Score: %s' % (score), True, WHITE)
    scoreRect = scoreSurf.get_rect()
    scoreRect.topleft = (WINDOWWIDTH - 120, 10)
    DISPLAYSURF.blit(scoreSurf, scoreRect)


def drawApple(coord):
    x = coord['x'] * CELLSIZE
    y = coord['y'] * CELLSIZE
    appleRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
    pygame.draw.rect(DISPLAYSURF, RED, appleRect)


def drawGrid():
    for x in range(0, WINDOWWIDTH, CELLSIZE): # draw vertical lines
        pygame.draw.line(DISPLAYSURF, DARKGRAY, (x, 0), (x, WINDOWHEIGHT))
    for y in range(0, WINDOWHEIGHT, CELLSIZE): # draw horizontal lines
        pygame.draw.line(DISPLAYSURF, DARKGRAY, (0, y), (WINDOWWIDTH, y))


if __name__ == '__main__':
    main()
    print("Game over")