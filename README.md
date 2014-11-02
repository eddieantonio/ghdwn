# Download Corpora

Download most popular projects for a given language.

 1. Obtain most popular projects list from GitHub.

    Parameters: 
	- LANGAUGE: programming language
	- QUANITY: number of projects

 2. Downloads the tarball of each project.

    1. Untars the project.
    2. Find all files of the given file type; deletes all others.
    3. Syntax checks all the files; prunes files that do not syntax-check.
    4. Moves files to the "good" index.

 3. Train corpus based on all of these files.

    1. can do these tasks in parallel.

