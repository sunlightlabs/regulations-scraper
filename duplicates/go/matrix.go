
package main

import (
    "fmt"
    "flag"
    "strconv"
    "rand"
    "time"
)


type Matrix [][]float32


func MatrixMin(m [][]float32) (int, int) {
    min_i := 0
    min_j := 0
    min_v := float32(1.0)
    
    for i, r := range m {
        for j, v := range r {
            if v < min_v {
                min_i = i
                min_j = j
                min_v = v
            } 
        }
    }
    
    return min_i, min_j
}


func RandMatrix(size int) Matrix {
    m := make([][]float32, size)
    
    for i := range m {
        m[i] = make([]float32, size)
        for j := range m[i] {
            m[i][j] = rand.Float32()
        }
    }
    
    return Matrix(m)
}


func main() {
    flag.Parse()
    n, _ := strconv.Atoi(flag.Arg(0))
    
    start := time.Nanoseconds()
    m := RandMatrix(n)
    end := time.Nanoseconds()
    fmt.Printf("Creating %v x %v matrix took %vms\n", n, n, (end - start) / 1000000.0)
    
    start = time.Nanoseconds()
    i, j := MatrixMin(m)
    end = time.Nanoseconds()
    fmt.Printf("Finding min in %v x %v matrix took %vms\n", n, n, (end - start) / 1000000.0)
    fmt.Printf("Min was %f\n", m[i][j])
}

