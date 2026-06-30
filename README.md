# CFG Optimizer

A compiler optimization project that performs optimizations on Control Flow Graphs (CFG) to improve program efficiency and reduce redundant computations.

## Features

- Control Flow Graph (CFG) construction
- CFG analysis
- Optimization passes
- Easy to extend with additional compiler optimizations

## Project Structure

```
cfg_optimizer/
├── src/            # Source code
├── tests/          # Test cases
├── docs/           # Documentation
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/adi-2254/cfg_optimizer.git
cd cfg_optimizer
```

2. (Optional) Create a virtual environment:

```bash
python -m venv env
source env/bin/activate      # Linux/macOS
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the project:

```bash
python main.py
```

## Technologies Used

- Python
- Compiler Design
- Control Flow Graph (CFG)

## Future Improvements

- Dead Code Elimination
- Constant Folding
- Constant Propagation
- Common Subexpression Elimination
- Loop Optimizations

## License

This project is licensed under the MIT License.
