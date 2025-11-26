import { addMatrices, multiplyMatrices, transpose, assertMatricesDimensionMatch, assertMatricesCompatible } from "./matrix-operations";
import { fromJSONFile, jsonFilePath, randomizeMatrix, randomizeVector } from "./utils";
import { vectorSum, dotProduct } from "./vector-operations";
import { Matrix, Vector } from "./types";
import { displayVector, displayMatrix } from "./display";

// HINT: (w zaleności od wybranego kierunku implementacji) może być mnożenie macierzy przez wektory - tę operację będzie trzeba zaimplementować 😉 
// ale nie jest to konieczne 😎

// HINT: w mnożeniu macierzy kolejność ma znaczenie - bo w zależności od kolejności albo wymiary obydwu składników pasują do siebie albo nie.

// HINT: wstań od komputera i przemyśl problem. Serio. Zastanów się, ile linijek wystarczy aby podać rozwiązanie :)
// (traktując "linijkę" jako pojedynczą operację na tensorach) 😎

// PROŚBA: jeśli znasz rozwiązanie, to nie spamuj discorda - a przynajmniej nie od razu. Pozwól innym pomóżdżyć 😎

//const { WK_Matrix, WQ_Matrix, X_Input_Matrix } = fromJSONFile(jsonFilePath('case-1.json'));
// const { WK_Matrix, WQ_Matrix, X_Input_Matrix } = fromJSONFile(jsonFilePath('case-2.json'));
//const { WK_Matrix, WQ_Matrix, X_Input_Matrix } = fromJSONFile(jsonFilePath('case-3.json'));
const { WK_Matrix, WQ_Matrix, X_Input_Matrix } = fromJSONFile(jsonFilePath('case-4.json'));

console.log('WK_Matrix');
console.log(displayMatrix(WK_Matrix, -1));
console.log('WQ_Matrix');
console.log(displayMatrix(WQ_Matrix, -1));
console.log('X_Input_Matrix');
console.log(displayMatrix(X_Input_Matrix, -1));

const x1_vector = X_Input_Matrix[0];
console.log('x1_vector');
console.log(displayVector(x1_vector, -1));

// przypomnienie zadania: naley policzyć "attention matrix S"

// for each input vector xi in X_Input_Matrix:
//   compute query vector qi = WQ * xi
//   compute key vector ki = WK * xi
//
// for each pair of input vectors (xi, xj):
//   compute attention score Sij = dot(qi, kj)
//
// return attention matrix S

// YOUR CODE HERE

// krok 1: oblicz wektory zapytań (Q) i kluczy (K) dla każdego wektora wejściowego
const Q_Matrix: Matrix = multiplyMatrices(X_Input_Matrix, WQ_Matrix);

const K_Matrix: Matrix = multiplyMatrices(X_Input_Matrix, WK_Matrix);

const S_Matrix: Matrix = multiplyMatrices(Q_Matrix, transpose(K_Matrix))

// krok 2: oblicz macierz uwagi S
console.log('Attention Matrix S:');
console.log(displayMatrix(S_Matrix, -1));

