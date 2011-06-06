
package main

import (
    "testing"
    "fmt"
    "time"
)


func BenchmarkMatrix(t *testing.T) {
    m := RandMatrix(b.N)
    start := time.Nanoseconds()
    MatrixMin(m)
    end := time.Nanoseconds()
    fmt.Printf("")
}