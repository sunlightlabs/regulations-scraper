function MatrixMin(m) {
    var min_i = 0;
    var min_j = 0;
    var min_v = 1.0;
    
    n = m.length;
    
    for (var i = 0; i < n; i++) {
        for (var j = 0; j < n; j++) {
            if (m[i][j] < min_v) {
                min_i = i;
                min_j = j;
                min_v = m[i][j];
            }
        }
    }

    return [min_i, min_j];
}

function RandMatrix(n) {
    m = [];
    
    for (var i = 0; i < n; i++) {
        m[i] = [];
        for (var j = 0; j < n; j++) {
            m[i][j] = Math.random();
        }
    }
    
    return m;
}

var n = parseInt(process.argv[2]);

var start = Date.now();
var m = RandMatrix(n);
var end = Date.now();
console.log("Creating " + n + " x " + n + " matrix took " + (end - start) + "ms");

start = Date.now();
var min = MatrixMin(m);
end = Date.now();
console.log("Finding " + n + " x " + n + " matrix took " + (end - start) + "ms");
console.log("Min was " + m[min[0]][min[1]]);

