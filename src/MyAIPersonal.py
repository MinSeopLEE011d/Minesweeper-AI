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
	def __init__(self, rowDimension, colDimension, totalMines, startX, startY):
		# Number of tiles that still need to be uncovered
		self.__uncoveredLeft: int = rowDimension * colDimension - totalMines - 1
		# x and y values of previous action
		self.__lastX: int = startX
		self.__lastY: int = startY

		# Agents information on the game grid
		self.__grid: GameGrid = GameGrid(colDimension, rowDimension)

		# Queues for both types of actions
		self.__uncoverSet: set = set()
		self.__flagSet: set = set()
		# Set for which tiles to search off of
		self.__searchSet: set = set()

		# Add starting tile to explore queue
		#self.__exploreQueue.tryPush((startX, startY))
		self.__grid.updateState(startX, startY, 0)

	
	def getAction(self, number: int) -> "Action Object": # type: ignore
		########################################################################
		#							YOUR CODE BEGINS						   #
		########################################################################
		percept: int = number
		lastX: int = self.__lastX
		lastY: int = self.__lastY
		grid: GameGrid = self.__grid

		uncoverSet: set = self.__uncoverSet
		flagSet: set = self.__flagSet
		searchSet: set = self.__searchSet
		
		# DEBUG
		#print(f"ExploreQ: {exploreQueue.debugStr()}")
		#print(f"FlagQ:    {flagQueue.debugStr()}")

		if self.__uncoveredLeft == 0:
			return Action(AI.Action.LEAVE)

		grid.updateState(lastX, lastY, percept)

		if percept == 0:
			uncoverSet.update(grid.adjacentUnknownList(lastX, lastY))
		
		if percept > 0:
			searchSet.add((lastX, lastY))

		if percept >= 0:
			searchSet.update(grid.adjacentDangerList(lastX, lastY))

		# Add any tiles to the explore and flag queue based on the info we know.
		while searchSet:
			x,y = searchSet.pop()
			danger = grid.getState(x,y)
			if danger == grid.adjacentFlagged(x,y):
				uncoverSet.update(grid.adjacentUnknownList(x,y))
			elif danger == grid.adjacentFlagged(x,y) + grid.adjacentUnknown(x,y):
				flagSet.update(grid.adjacentUnknownList(x,y))
			else:
				knownSafeTiles, knownMines = grid.shallowSearch(x,y)
				uncoverSet.update(knownSafeTiles)
				uncoverSet.update(knownMines)
		
		# Guessing placeholder code
		if not (uncoverSet or flagSet):
			uncoverSet.add(grid.randomUncovered()) # Change to guessUncovered?

		# If the explore queue has something, take an action from it.
		if uncoverSet:
			x,y = uncoverSet.pop()
			self.__uncoveredLeft -= 1
			self.__updateLastPos(x, y)
			return Action(AI.Action.UNCOVER, x, y)
		
		# Explore queue was empty, but we have items to flag.
		x,y = flagSet.pop()
		self.__updateLastPos(x, y)
		searchSet.update(grid.adjacentDangerList(x, y))
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
	

	def updateState(self, c: int, r: int, percept: int) -> None:
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

	
	def shallowSearch(self, x, y) -> tuple[list[tuple[int,int]],list[tuple[int,int]]]:
		"""
		Performs a shallow search by iterating each configuation of the surrounding
		unknown tiles and finding commonalitlies between all valid combinations.
		Returns a tuple where the first item is a list of all known safe tiles from
		the search and the second item is a list of all known mine locations from
		the search.
		"""
		danger = self.getState(x,y)
		flagged = self.adjacentFlagged(x,y)
		unknown = self.adjacentUnknown(x,y)
		if danger == flagged + unknown - 1:
			return self.__searchOneSafe(x,y)
		if danger == unknown + 1:
			return self.__searchOneMine(x,y)
		return [], []

	def __searchOneSafe(self, x, y) -> tuple[list[tuple[int,int]],list[tuple[int,int]]]:
		"""Search case for when we know exactly one unknown adjacent space is safe."""
		# Get lists of search and validation tiles
		searchTiles: list[tuple[int,int]] = self.adjacentUnknownList(x,y)
		validationTiles: set[tuple[int,int]] = set()
		configurations: list[list[tuple[int,int]]] = []
		for searchX,searchY in searchTiles:
			validationTiles.update(self.adjacentDangerList(searchX, searchY))
		for i in range(len(searchTiles)):
			# Set up search configuration
			self.updateState(searchTiles[i-1][0], searchTiles[i-1][1], State.FLAG)
			self.updateState(searchTiles[i][0], searchTiles[i][1], 0)
			




	def __searchOneMine(self, x, y) -> tuple[list[tuple[int,int]],list[tuple[int,int]]]:
		"""Search case for when we know exactly one unknown adjacent space is a mine."""


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
		

