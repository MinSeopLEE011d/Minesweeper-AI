from AI import AI
from Action import Action

from enum import Enum
from enum import IntEnum
from itertools import combinations


class State(IntEnum):
	"""
	Using only negative values to allow one grid value to be able to represent
	a danger level or any other tile state. This also makes it easy to check
	if a grid space has already been uncovered with a known danger value.

	FLAG is assigned to -1 to make it consistent with the fact that the world
	returns a percept of -1 when we flag a tile.
	"""
	FLAG = -1
	UNKNOWN = -2
	BORDER = -3 # Out of bounds

class SearchType(Enum):
	"""Enum for search types."""
	ONE_SAFE = 0
	ONE_FLAG = 1


class MyAI( AI ):
	def __init__(self, rowDimension, colDimension, totalMines, startX, startY):
		self.__uncoveredLeft: int = rowDimension * colDimension - totalMines - 1
		self.__totalMines: int = totalMines

		self.__lastX: int = startX
		self.__lastY: int = startY

		self.__grid: GameGrid = GameGrid(colDimension, rowDimension)
		baseProb: float = totalMines / (rowDimension * colDimension)
		self.__pscores: list[list] = [[baseProb for _ in range(rowDimension)] for _ in range(colDimension)] #PLACEHOLDER VALUE

		self.__safeSet: set = set()    # Tiles we know are safe (need to uncover)
		self.__toFlagSet: set = set()  # Tiles we know have mines (need to flag)
		self.__searchSet: set = set()  # Set of tiles to search

	
	def getAction(self, number: int) -> "Action Object": # type: ignore
		percept: int = number
		lastX: int = self.__lastX
		lastY: int = self.__lastY
		grid: GameGrid = self.__grid

		safeSet: set = self.__safeSet
		toFlagSet: set = self.__toFlagSet
		searchSet: set = self.__searchSet

		if self.__uncoveredLeft == 0:
			return Action(AI.Action.LEAVE)
		
		grid.updateState(lastX, lastY, percept)

		# Update sets
		if percept >= 0:
			if percept == 0:
				safeSet.update(grid.getAdjUnknownList(lastX, lastY))
			else:
				searchSet.add((lastX, lastY))
			searchSet.update(grid.getAdjDangerList(lastX, lastY))
		
		# OPTIMIZATION: (If all mines found, add all unknown tiles to safe set)
		# Search
		while searchSet:
			x,y = searchSet.pop()
			danger = grid.getState(x,y)
			numAdjFlagged = grid.getNumAdjFlagged(x,y)
			numAdjUnknown = grid.getNumAdjUnknown(x,y)

			if danger == numAdjFlagged:
				safeSet.update(grid.getAdjUnknownList(x,y))
			elif danger == numAdjFlagged + numAdjUnknown:
				toFlagSet.update(grid.getAdjUnknownList(x,y))
			elif danger == numAdjFlagged + numAdjUnknown - 1:
				safeTiles, mines = self.__shallowSearch(x,y,SearchType.ONE_SAFE)
				safeSet.update(safeTiles)
				toFlagSet.update(mines)
			elif danger == numAdjFlagged + 1:
				safeTiles, mines = self.__shallowSearch(x,y,SearchType.ONE_FLAG)
				safeSet.update(safeTiles)
				toFlagSet.update(mines)
			else:
				safeTiles, mines = self.__semiShallowSearch(x,y)
				safeSet.update(safeTiles)
				toFlagSet.update(mines)
		
		# Guessing/probability heuristics
		if not (safeSet or toFlagSet):
			safeSet.add(self.__guessSafeTile())

		# Make move from safe set
		if safeSet:
			x,y = safeSet.pop()
			self.__uncoveredLeft -= 1
			self.__updateLastPos(x,y)
			return Action(AI.Action.UNCOVER, x, y)
		
		# Make move from flag set
		x,y = toFlagSet.pop()
		self.__updateLastPos(x,y)
		searchSet.update(grid.getAdjDangerList(x,y))
		return Action(AI.Action.FLAG, x, y)
	

	def __updateLastPos(self, x: int, y: int):
		"""Update last position for updating board info on next turn."""
		self.__lastX, self.__lastY = x, y


	def __guessSafeTile(self) -> tuple[int, int]:
		"""Probability heuristic (Edward)"""
		grid: GameGrid = self.__grid
		# Recalculate/update pScores
		for x in range(grid.getNumCols()):
			for y in range(grid.getNumRows()):
				danger = grid.getState(x,y)
				numAdjUnknown = grid.getNumAdjUnknown(x,y)
				numAdjMines = grid.getNumAdjFlagged(x,y)
				if danger > 0 and numAdjUnknown != 0:
					prob = (danger - numAdjMines) / numAdjUnknown
					for x,y in grid.unknownSet:
						if prob == 0 or self.__pscores[x][y] < prob:
							self.__pscores[x][y] = prob
		min_value: float = 1.0
		min_x, min_y = 0, 0
		for x in range(grid.getNumCols()):
			for y in range(grid.getNumRows()):
				if grid.getState(x,y) == State.UNKNOWN and self.__pscores[x][y] < min_value:
					min_value = self.__pscores[x][y]
					min_x, min_y = x, y
					if (min_value == 0):
						return (min_x, min_y)
		return min_x, min_y



	def __shallowSearch(self, x: int, y: int, searchType: SearchType) -> tuple[list[tuple[int,int]],list[tuple[int,int]]]:
		"""
		Performs a shallow search by iterating each configuation of the surrounding
		unknown tiles and finding commonalitlies between all valid combinations.
		Returns a tuple where the first item is a list of all known safe tiles from
		the search and the second item is a list of all known mine locations from
		the search.
		"""
		grid = self.__grid

		oneSafeMode: bool = searchType == SearchType.ONE_SAFE

		searchTiles: list[tuple[int,int]] = grid.getAdjUnknownList(x,y)

		validationTilesSet: set[tuple[int,int]] = set()
		for sX,sY in searchTiles:
			validationTilesSet.update(grid.getAdjDangerList(sX, sY))
		validationTilesSet.remove((x,y)) # This tile will always be valid, checking it is redundant
		validationTiles: list[tuple[int,int]] = list(validationTilesSet)

		# Initialize values of search tile grid spaces
		if oneSafeMode:
			for sX,sY in searchTiles:
				grid.setState(sX, sY, State.FLAG)
		else:
			for sX,sY in searchTiles:
				grid.setState(sX, sY, 0)
		
		# Create list for storaing valid tile configs
		# True = safe, False = mine
		validConfigs: list[list[bool]] = []
		# Check configuration for each tile having a different assignment
		for i in range(len(searchTiles)):
			# Update to next configuration
			if oneSafeMode:
				grid.setState(searchTiles[i-1][0], searchTiles[i-1][1], State.FLAG)
				grid.setState(searchTiles[i][0], searchTiles[i][1], 0)
			else:
				grid.setState(searchTiles[i-1][0], searchTiles[i-1][1], 0)
				grid.setState(searchTiles[i][0], searchTiles[i][1], State.FLAG)
			
			# If the configuration is valid, store it
			valid: bool = True
			for vX,vY in validationTiles:
				if (grid.getNumAdjFlagged(vX,vY) + grid.getNumAdjUnknown(vX,vY) < grid.getState(vX,vY) or
						grid.getNumAdjFlagged(vX,vY) > grid.getState(vX,vY)):
					valid = False
					break
			if valid:
				if oneSafeMode:
					validConfigs.append([j == i for j in range(len(searchTiles))])
				else:
					validConfigs.append([j != i for j in range(len(searchTiles))])

		# Get indices of all tiles that are the same across valid configurations
		consistentIndices: list[int] = []
		for i in range(len(validConfigs[0])):
			consistent: bool = True
			for j in range(len(validConfigs) - 1):
				if validConfigs[j][i] != validConfigs[j+1][i]:
					consistent = False
					break
			if consistent:
				consistentIndices.append(i)
		
		safeTiles: list[tuple[int,int]] = []
		mines: list[tuple[int,int]] = []
		for i in consistentIndices:
			if validConfigs[0][i]:
				safeTiles.append(searchTiles[i])
			else:
				mines.append(searchTiles[i])
		
		for sX,sY in searchTiles:
			grid.setState(sX,sY,State.UNKNOWN)
		return safeTiles, mines
	

	def __semiShallowSearch(self, x: int, y: int) -> tuple[list[tuple[int,int]],list[tuple[int,int]]]:
		"""
		Performs a shallow search by iterating each configuation of the surrounding
		unknown tiles and finding commonalitlies between all valid combinations.
		Returns a tuple where the first item is a list of all known safe tiles from
		the search and the second item is a list of all known mine locations from
		the search. Takes more time than a shallow search and should not be used if
        any other search/logic can be applied first.
		"""
		grid = self.__grid
		numAdjUnknown = grid.getNumAdjUnknown(x,y)

		searchTiles: list[tuple[int,int]] = grid.getAdjUnknownList(x,y)

		validationTilesSet: set[tuple[int,int]] = set()
		for sX,sY in searchTiles:
			validationTilesSet.update(grid.getAdjDangerList(sX, sY))
		validationTiles: list[tuple[int,int]] = list(validationTilesSet)
		
		# Create a list for storing valid tile configs
		# True = safe, False = mine
		validConfigs: list[list[bool]] = []
		# Check each configuration
		searchIndices: list = [x for x in range(numAdjUnknown)]
		for i in range(2, numAdjUnknown - 1):
			for c in combinations(searchIndices, i):
    			# Update to next configuration
				config: list[bool] = [x in c for x in range(numAdjUnknown)]
				#print(f"Testing config ({i})", config)
				for j in range(len(config)):
					if config[j]:
						grid.setState(searchTiles[j][0], searchTiles[j][1], 0)
					else:
						grid.setState(searchTiles[j][0], searchTiles[j][1], State.FLAG)
                
    			# If the configuration is valid, store it
				valid: bool = True
				for vX,vY in validationTiles:
					if (grid.getNumAdjFlagged(vX,vY) + grid.getNumAdjUnknown(vX,vY) < grid.getState(vX,vY) or
    						grid.getNumAdjFlagged(vX,vY) > grid.getState(vX,vY)):
						valid = False
						break
				if valid:
					validConfigs.append(config)
		# Get indices of all tiles that are the same across valid configurations
		consistentIndices: list[int] = []
		for i in range(len(validConfigs[0])):
			consistent: bool = True
			for j in range(len(validConfigs) - 1):
				if validConfigs[j][i] != validConfigs[j+1][i]:
					consistent = False
					break
			if consistent:
				consistentIndices.append(i)
		#print("Consistent indices", consistentIndices)
		safeTiles: list[tuple[int,int]] = []
		mines: list[tuple[int,int]] = []
		for i in consistentIndices:
			if validConfigs[0][i]:
				safeTiles.append(searchTiles[i])
			else:
				mines.append(searchTiles[i])
		
		for sX,sY in searchTiles:
			grid.setState(sX,sY,State.UNKNOWN)
		return safeTiles, mines


class GameGrid:
	"""
	Class to keep track of the known game state.
	
	Internally, contains a grid that has 2 more columns and rows than the actual
	game grid to make space for border tiles to make some function implementations
	earlier.
	
	Note: When using helper functions, grid indices start at (0, 0).
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
		self.unknownSet: set[tuple[int, int]] = {
			(c, r) for r in range(numRows) for c in range(numCols)
		}


	def getNumRows(self) -> int:
		return self.__numRows

	
	def getNumCols(self) -> int:
		return self.__numCols
	

	def updateState(self, c: int, r: int, percept: int) -> None:
		"""Update the board information based on the percept from an action."""
		if c < 0 or r < 0 or c >= self.__numCols or r >= self.__numRows:
			raise ValueError(f"Coordinates {r},{c} out of bounds")
		self.unknownSet.discard((c, r))
		if percept >= 0:
			self.__grid[c+1][r+1] = percept
		else:
			self.__grid[c+1][r+1] = State.FLAG


	def setState(self, c: int, r: int, state: int) -> None:
		"""Directly set the state for a grid space."""
		if c < 0 or r < 0 or c >= self.__numCols or r >= self.__numRows:
			raise ValueError(f"Coordinates {r},{c} out of bounds")
		self.__grid[c+1][r+1] = state

	
	def getState(self, c: int, r: int) -> int:
		"""Returns the state of a tile."""
		return self.__grid[c+1][r+1]
	

	def __adjStateList(self, c: int, r: int, state: int):
		"""Helper function that returns coordinates of all adjacent tiles with a certain state."""
		return [
			(c+i-1, r+j-1)
			for i in range(3)
			for j in range(3)
			if (self.__grid[c+i][r+j] == state) and (i * j != 1)
		]


	def getAdjFlaggedList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent flagged tiles."""
		return self.__adjStateList(c, r, State.FLAG)
	

	def getAdjUnknownList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent unknown tiles."""
		return self.__adjStateList(c, r, State.UNKNOWN)
	

	def getAdjUncoveredList(self, c: int, r: int) -> list[tuple[int, int]]:
		"""Returns a list containing the coordinates of all adjacent uncovered tiles."""
		return [
			(c+i-1, r+j-1)
			for i in range(3)
			for j in range(3)
			if (self.__grid[c+i][r+j] >= 0) and (i * j != 1)
		]
	

	def getAdjDangerList(self, c: int, r: int) -> list[tuple[int, int]]:
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

	
	def getNumAdjFlagged(self, c: int, r: int) -> int:
		"""Returns number of adjacent tiles that are flagged."""
		return len(self.getAdjFlaggedList(c, r))
	

	def getNumAdjUnknown(self, c: int, r: int) -> int:
		"""Returns number of adjacent tiles that are unknown."""
		return len(self.getAdjUnknownList(c, r))
	

	def debugGrid(self) -> None:
		"""
		(DEBUG) Print AI's knowledge of the entire grid.

		NOTE: This grid visualizer starts indexing at 0 to make it easier to debug
		using the AI's information. This is different than the server's board
		display that starts indexing at 1.
		
		`.` Border,
		`X` Flag,
		`.` Unknown,
		`E` ERROR (This value should not exist in a grid space and something has gone wrong)
		"""
		for i in range(self.__numRows, 0, -1):
			line: str = f"{str(i-1).rjust(2)} | "
			for j in range(1, self.__numCols + 1):
				state = self.__grid[j][i]
				if state >= 0:
					line += str(state) + " "
				elif state == State.FLAG:
					line += "X" + " "
				elif state == State.UNKNOWN:
					line += "." + " "
				else:
					line += "E" + " "
			print(line)
		line: str = "AI +"
		for i in range(1, self.__numCols + 1):
			line += "--"
		print(line)
		line = "GRID"
		for i in range(1, self.__numCols + 1):
			line += f"{str(i-1).rjust(2)}"
		print(line)
		
