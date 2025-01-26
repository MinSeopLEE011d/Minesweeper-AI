# ==============================CS-199==================================
# FILE:			MyAI.py
#
# AUTHOR: 		Justin Chung
#
# DESCRIPTION:	This file contains the MyAI class. You will implement your
#				agent in this file. You will write the 'getAction' function,
#				the constructor, and any additional helper functions.
#
# NOTES: 		- MyAI inherits from the abstract AI class in AI.py.
#
#				- DO NOT MAKE CHANGES TO THIS FILE.
# ==============================CS-199==================================

from AI import AI
from Action import Action

from typing import Any
from collections import deque
from enum import IntEnum

import random


class MyAI( AI ):
	## Don't modify function parameters!
	def __init__(self, rowDimension, colDimension, totalMines, startX, startY):
		# Number of tiles that still need to be uncovered
		self.__uncoveredLeft: int = rowDimension * colDimension - totalMines - 1
		self.__totalMines: int = totalMines
		# x and y values of previous action
		self.__lastX: int = startX
		self.__lastY: int = startY

		# Agents information on the game grid
		self.__grid: GameGrid = GameGrid(colDimension, rowDimension)

		# Queues for both types of actions
		self.__exploreQueue = UniqueQueue()
		self.__flagQueue = UniqueQueue()
		# Queue for checking tiles
		self.__checkQueue = UniqueQueue()

		# Add starting tile to explore queue
		#self.__exploreQueue.tryPush((startX, startY))
		self.__grid.update(startX, startY, 0)

	
	# Don't modify function parameters!
	def getAction(self, number: int) -> "Action Object": # type: ignore
		########################################################################
		#							YOUR CODE BEGINS						   #
		########################################################################
		percept: int = number # 'number' is vague. Using 'percept' instead.
		# To avoid typing the whole thing. THIS IS A COPY NOT A REFERENCE.
		lastX: int = self.__lastX
		lastY: int = self.__lastY
		# Aliases for quickly accessing member data structures
		# Not sure if this is actually a good way of doing things but it does work.
		grid: GameGrid = self.__grid

		exploreQueue: UniqueQueue = self.__exploreQueue
		flagQueue: UniqueQueue = self.__flagQueue
		checkQueue: UniqueQueue = self.__checkQueue
		
		# DEBUG
		#print(f"ExploreQ: {exploreQueue.debugStr()}")
		#print(f"FlagQ:    {flagQueue.debugStr()}")

		if self.__uncoveredLeft == 0:
			return Action(AI.Action.LEAVE)

		self.__grid.update(lastX, lastY, percept)

		if percept == 0:
			exploreQueue.tryPushList(grid.adjacentUnknownList(lastX, lastY))
		
		if percept > 0:
			checkQueue.tryPush((lastX, lastY))

		if percept >= 0:
			checkQueue.tryPushList(grid.adjacentDangerList(lastX, lastY))

		# Add any tiles to the explore and flag queue based on the info we know.
		while checkQueue.notEmpty():
			x,y = checkQueue.pop()
			danger = grid.getState(x,y)
			if danger == grid.adjacentFlagged(x,y):
				exploreQueue.tryPushList(grid.adjacentUnknownList(x,y))
			elif danger == grid.adjacentFlagged(x,y) + grid.adjacentUnknown(x,y):
				flagQueue.tryPushList(grid.adjacentUnknownList(x,y))
		
		# No known safe options left. Add a random tile to the explore queue.
		if exploreQueue.empty() and flagQueue.empty():
			exploreQueue.tryPush(grid.randomUncovered())

		# If the explore queue has something, take an action from it.
		if exploreQueue.notEmpty():
			x,y = exploreQueue.pop()
			self.__uncoveredLeft -= 1
			self.__updateLastPos(x, y)
			return Action(AI.Action.UNCOVER, x, y)
		
		# Explore queue was empty, but we have items to flag.
		x,y = flagQueue.pop()
		self.__updateLastPos(x, y)
		checkQueue.tryPushList(grid.adjacentDangerList(x, y))
		return Action(AI.Action.FLAG, x, y)
		
		########################################################################
		#							YOUR CODE ENDS							   #
		########################################################################
	
	def __updateLastPos(self, x: int, y: int):
		"""Update last position for updating board info on next turn."""
		self.__lastX, self.__lastY = x, y


class State(IntEnum):
		"""
		Using only negative values to allow one grid value to be able to represent
		a danger level or any other tile state. This also makes it easy to check
		if a grid space has already been uncovered with a known danger value.
		"""
		UNKNOWN = -1
		FLAG = -2
		BORDER = -3 # Out of bounds


class UniqueQueue:
	"""A queue that does not allow for duplicate values."""
	def __init__(self):
		self.__queue = deque()
		self.__values = set()
	
	
	def __str__(self):
		return str(self.__queue)


	def tryPush(self, val) -> bool:
		"""
		Pushes a value to the queue if it is not already in it. Returns whether
		or not the value was added (might use for debugging).
		"""
		if val not in self.__values:
			self.__queue.append(val)
			self.__values.add(val)
			return True
		return False
	

	def tryPushList(self, vals: list) -> None:
		"""Pushes all items from a list to the queue. Ignores any items already in the queue."""
		for val in vals:
			self.tryPush(val)
			


	def pop(self) -> Any:
		"""Pops and returns the first added item from the queue."""
		val = self.__queue.popleft()
		self.__values.remove(val)
		return val


	def empty(self) -> bool:
		"""Returns whether the queue is empty."""
		return len(self.__queue) == 0
	

	def notEmpty(self) -> bool:
		"""Returns whether the queue is not empty."""
		return len(self.__queue) != 0
	

	def debugStr(self) -> str:
		"""For debug printing a queue of coordinates. Adds 1 offset."""
		string: str = ""
		for val in self.__queue:
			string += f"({val[0]+1},{val[1]+1}) "
		return string[:-1]


class GameGrid:
	"""
	Class to keep track of the known game state.
	
	Internally, contains a grid that has 2 more columns and rows than the actual
	game grid to make space for border tiles to make some function implementations
	earlier.
	
	Note To Self: If something isn't working, you probably forgot to account for
	the offset from the border when indexing.
	"""
	def __init__(self, numCols: int, numRows: int):
		# Create the grid
		self.__numCols: int = numCols
		self.__numRows: int = numRows
		numCols2 = numCols + 2
		numRows2 = numRows + 2
		self.__grid: list[list] = [[State.UNKNOWN for _ in range(numRows2)] for _ in range(numCols2)]
		# Create the border of the grid
		for i in range(numCols2):
			self.__grid[i][0] = State.BORDER
			self.__grid[i][numRows2-1] = State.BORDER
		for i in range(numRows2):
			self.__grid[0][i] = State.BORDER
			self.__grid[numCols2-1][i] = State.BORDER
		# Create a set for keeping track of the unknown tiles
		self.__unknownSet: set[tuple[int, int]] = {
			(c, r) for r in range(numRows) for c in range(numCols)
		}
	

	def update(self, c: int, r: int, percept: int) -> None:
		"""
		Update the board information based on the position of the last action
		and the percept given to the agent from that action.
		"""
		if c < 0 or r < 0 or c >= self.__numCols or r >= self.__numRows:
			raise ValueError(f"Coordinates {r},{c} out of bounds")
		self.__unknownSet.discard((c, r))
		if percept >= 0:
			self.__grid[c+1][r+1] = percept
		else:
			self.__grid[c+1][r+1] = State.FLAG


	def getState(self, c: int, r: int) -> int:
		"""Returns the state of a tile."""
		return self.__grid[c+1][r+1]


	def __adjacentStateList(self, c: int, r: int, state: int):
		"""Helper function that returns coordinates of all adjacent tiles with a certain state."""
		return [
			(c+i-1, r+j-1)
			for i in range(3)
			for j in range(3)
			if (self.__grid[c+i][r+j] == state) and (i * j != 1)
		]


	def adjacentFlaggedList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent flagged tiles."""
		return self.__adjacentStateList(c, r, State.FLAG)
	

	def adjacentUnknownList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent unknown tiles."""
		return self.__adjacentStateList(c, r, State.UNKNOWN)
	

	def adjacentUncoveredList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent uncovered tiles."""
		return [
			(c+i-1, r+j-1)
			for i in range(3)
			for j in range(3)
			if (self.__grid[c+i][r+j] >= 0) and (i * j != 1)
		]
	

	def adjacentDangerList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""
		Returns a list containing the coordinates of all adjacent uncovered tiles
		with a number greater than 0.
		"""
		return [
			(c+i-1, r+j-1)
			for i in range(3)
			for j in range(3)
			if (self.__grid[c+i][r+j] > 0) and (i * j != 1)
		]

	
	def adjacentFlagged(self, c: int, r: int) -> int:
		"""Returns number of adjacent tiles that are flagged."""
		return len(self.adjacentFlaggedList(c, r))
	

	def adjacentUnknown(self, c: int, r: int) -> int:
		"""Returns number of adjacent tiles that are unknown."""
		return len(self.adjacentUnknownList(c, r))
	

	def randomUncovered(self) -> tuple[int, int]:
		"""Returns the coordinates of a random unknown tile."""
		return random.choice(list(self.__unknownSet))


	def debugGrid(self) -> None:
		"""
		(DEBUG) Print information for the entire grid.
		
		`.` Border,
		`X` Flag,
		`?` Unknown,
		`E` ERROR (This value should not exist in a grid space and something has gone wrong)
		"""
		for i in range(self.__numRows + 2):
			line: str = ""
			for j in range(self.__numCols + 2):
				state = self.__grid[j][i]
				if state >= 0:
					line += str(state) + " "
				elif state == State.BORDER:
					line += "." + " "
				elif state == State.FLAG:
					line += "X" + " "
				elif state == State.UNKNOWN:
					line += "?" + " "
				else:
					line += "E" + " "
			print(line)
	

	def debugUnknownSet(self) -> None:
		"""(DEBUG) Print the coordinates of all unknown tiles."""
		print(self.__unknownSet)
		

