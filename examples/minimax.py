import chess
import random


class Person:
  def __init__(self, name, age):
    self.name = name
    self.age = age


p1 = Person("None",0)

p1.Q = 9;p1.q = -9;p1.R = 5;p1.r = -5;p1.N = 3;p1.n = -3;p1.B=3;p1.b=-3;p1.P=1;p1.p=-1;p1.K=0;p1.k=0;

def evaluate(pos) :
 
        evaluation = 0
	
        for place in chess.SQUARES : 
            p2=pos.piece_at(place)
            if p2 != None :
                 evaluation = evaluation + getattr(p1,str(p2))

        return evaluation

def minimax(position, depth,maximizingPlayer):
    if depth == 0 :
        return (evaluate(position), None)
    else: 
        if maximizingPlayer :
            bestscore = -float("inf")
            bestmove = None
            for move in position.legal_moves:
                position.push(move)
                score = minimax(position, depth - 1,False)[0]
                position.pop()				
                if score > bestscore: 
                    bestscore = score
                    bestmove = move
					
			 
            return (bestscore, bestmove)
        else:
            bestscore = float("inf")
            bestmove = None
            for move in position.legal_moves:
                position.push(move)
                score = minimax(position, depth - 1,True)[0]
                position.pop()
                if score < bestscore: 
                    bestscore = score
                    bestmove = move
					               
					
            return (bestscore, bestmove)
			
def alphabeta(position, depth, alpha, beta,maximizingPlayer):

    if depth == 0 :
        return (evaluate(position), None)
    else: 
        if maximizingPlayer :
            bestmove = None
            for move in position.legal_moves:
                position.push(move)
                score = alphabeta(position, depth - 1, alpha, beta,False)[0]
                position.pop()
                if score > alpha: # white maximizes her score
                    alpha = score
                    bestmove = move
                    if alpha >= beta: # alpha-beta cutoff
                        break
						
                
						
            return (alpha, bestmove)
        else:
            bestmove = None
            for move in position.legal_moves:
                position.push(move)
                score = alphabeta(position, depth - 1, alpha, beta,True)[0]
                position.pop()
                if score < beta: # black minimizes his score
                    beta = score
                    bestmove = move
                    if alpha >= beta: # alpha-beta cutoff
                        break
						
                
						
            return (beta, bestmove)		

def negamax(position, depth, alpha, beta,maximizingPlayer):

    if depth == 0 :
      return (evaluate(position), None) if maximizingPlayer else (-evaluate(position), None)
    else: 
            bestmove = None
            for move in position.legal_moves:
                position.push(move)
                score = -negamax(position, depth - 1, -beta, -alpha,not maximizingPlayer)[0]
                position.pop()
                if score > alpha: # white maximizes her score
                    alpha = score
                    bestmove = move
                    if alpha >= beta: # alpha-beta cutoff
                        break
						
                
						
            return (alpha, bestmove)
	
board=chess.Board('r1b1kbnr/pppp1ppp/2n5/4p1q1/4P3/P4N2/1PPP1PPP/RNBQKB1R w KQkq - 1 4');


#for x in board.legal_moves:
#  print(x) 
 
print('Calculating,please wait...') 
#print(minimax(board,3,True));
#print(alphabeta(board,5,-float("inf"),float("inf"),True));
print(negamax(board,5,-float("inf"),float("inf"),True));
