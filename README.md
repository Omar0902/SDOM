# Storage Deployment Optimization Model (SDOM) 🔋
SDOM is a high-resolution grid planning framework designed to optimize the deployment and operation of energy storage technologies across diverse temporal and spatial scales. It is particularly suited for evaluating long-duration and seasonal storage applications, as well as the complementarity among variable renewable energy (VRE) sources.

## Table of contents
- [Key Features ⚙️](#key-features-️)
- [Optimization Scope 📉](#optimization-scope-)
- [Notes on Model Expansion](#notes-on-model-expansion)
- [PUBLICATIONS AND USE CASES OF SDOM 📄](#publications-and-use-cases-of-sdom-)
- [CONTRIBUTING GUIDELINES](#contributing-guidelines)

# Key Features ⚙️
- Temporal Resolution: Hourly simulations over a full year enable precise modeling of storage dynamics and renewable generation variability.

- Spatial Resolution: Fine-grained representation of VRE sources (e.g., solar, wind) captures geographic diversity and enhances system fidelity.

- Copper Plate Modeling: SDOM Model neglects transmission constraints to keep the model tractable from the computational standpoint. Future SDOM releases should include inter-regional transmission constraints.

- Fixed Generation Profiles: Nuclear, hydropower, and other non-variable renewables (e.g., biomass, geothermal) are treated as fixed inputs using year-long time series data.

- System Optimization Objective: Minimizes total system cost—including capital, fixed/variable O&M, and fuel costs—while satisfying user-defined carbon-free or renewable energy targets.

- Modeling approach: Formulated as a Mixed-Integer Linear Programming (MILP) model to allow rigorous optimization of discrete investment and operational decisions.

- Platforms: SDOM was originally developed in GAMS (https://github.com/NREL/SDOM). In order offer a full open-source solution also was developed this python package.

## Optimization Scope 📉
SDOM performs cost minimization across a 1-year operation window using a copper plate assumption—i.e., no internal transmission constraints—making it computationally efficient while capturing major cost drivers. Conventional generators are used as balancing resources, and storage technologies serve to meet carbon or renewable penetration goals.

## Notes on Model Expansion
While SDOM currently supports a 1-year horizon, multiyear analyses could provide deeper insights into how interannual variability affects storage needs. Chronological, simulation-based approaches are better suited for this but present significant computational challenges—especially at hourly resolution. Extending SDOM to support multiyear optimization is left as future work.

# PUBLICATIONS AND USE CASES OF SDOM 📄
- Original SDOM paper:
  - Guerra, O. J., Eichman, J., & Denholm, P. (2021). Optimal energy storage portfolio for high and ultrahigh carbon-free and renewable power systems. *Energy Environ. Sci.*, 14(10), 5132-5146. https://doi.org/10.1039/D1EE01835C
  - NREL media relations (2021). Energy Storage Ecosystem Offers Lowest-Cost Path to 100% Renewable Power. https://www.nrel.gov/news/detail/program/2021/energy-storage-ecosystem-offers-lowest-cost-path-to-100-renewable-power

- SDOM GAMS version software registration:
- Uses cases in the "Renewables in Latin America and the Caribbean" or RELAC initiative (Uruguay, Peru, El Salvador)
  - Guerra, O. J., et al. (2023). Accelerated Energy Storage Deployment in RELAC Countries. *National Renewable Energy Laboratory (NREL)*. https://research-hub.nrel.gov/en/publications/accelerated-energy-storage-deployment-in-relac-countries

- Guerra, O. J., et al. (2022). Optimizing Energy Storage for Ultra High Renewable Electricity Systems. Conference for Colorado Renewable Energy society. https://www.youtube.com/watch?v=SYTnN6Z65kI 

# CONTRIBUTING GUIDELINES

## General Guidelines

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style and formatting.
- Write clear, concise, and well-documented code.
- Add docstrings to all public classes, methods, and functions.
- Include unit tests for new features and bug fixes.
- Use descriptive commit messages.
- Open issues or discussions for significant changes before submitting a pull request.
- Ensure all tests pass before submitting code.
- Keep dependencies minimal and document any new requirements.
- Review and update documentation as needed.
- Be respectful and collaborative in all communications.

Please see a complete developers guide here:
[Developers Guide](./Developers_guide.md) 
